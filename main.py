from concurrent.futures import process
import pipeline
import csv
import argparse
import pymongo
import pandas as pd
import os
from dotenv import load_dotenv

import sys
import vimeo
import time

#To Run the script, use the following command:
#python main.py --baselight baselight.txt --xytech xytech.txt --process video
#Example: python main.py --baselight Baselight.txt --xytech Xytech.txt --process TestVideo.mp4 --output

Location_Frames = []
allThumbnails = []
        
def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--baselight", nargs="+", required=True)
    parser.add_argument("--xytech", nargs="+", required=True)
    parser.add_argument("--process", nargs="+")
    parser.add_argument("--output", action="store_true")
    args = parser.parse_args()

    if args.output and not args.process:
        print("ERROR: You must provide --process when giving --output")

    client = None

    if args.output:
        client = vimeo.VimeoClient(
            token=os.environ['VIMEO_ACCESS_TOKEN'],
            key=os.environ['VIMEO_CLIENT_ID'],
            secret=os.environ['VIMEO_CLIENT_SECRET']
        )


    #Initilize Database
    myclient = pymongo.MongoClient(os.environ["MONGODB_URI"])

    myclient.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")

    mydb = myclient["media_pipeline_demo"]

    baselightCol = mydb["baselight"]
    xytechCol = mydb["xytech"]
    baselightCol.drop()
    xytechCol.drop()

    #Loads baselight into DB
    for baselight_file in args.baselight:
        with open(baselight_file, "r") as baselight:
            tempBaselightDict = pipeline.load_baselight(baselight)
            document = [{"shot": s, "frames": f} for s, f in tempBaselightDict.items()]
            baselightCol.insert_many(document)

    #Loads xytech into DB
    for xytech_file in args.xytech:
        with open(xytech_file, "r") as xytech:
            tempXytechDict = pipeline.load_xytech(xytech)
            document = [{"workorder": w, "directories": d} for w, d in tempXytechDict.items()]
            xytechCol.insert_many(document)

    # Extracts the Data from baselight collection
    baselightDict = {doc["shot"]: doc["frames"] for doc in baselightCol.find()}
    # Extracts the Data from xytech collection
    xytechDict = {doc["workorder"]: doc["directories"] for doc in xytechCol.find()}

    #Compare Location and create the correct directory
    frameDirectory = pipeline.comparison_algorithm(baselight=baselightDict, xytech=xytechDict)
    frameRanges = pipeline.frame_ranges(frameDirectory)

    #Sort the data by Frames
    Sorted_frameRanges = sorted(frameRanges, key=lambda x: int(x[1].split("-")[0]))

    #Seperate solo-frames and frame-ranges
    framesWithLocations = pipeline.seperate_frames(Sorted_frameRanges)
    shots = framesWithLocations[0] #Frame Ranges
    soloShots = framesWithLocations[1] #Seperate Frames

    if not args.output:
        with open('output.csv', "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(Sorted_frameRanges)
    #Timecode/Main---------------------------------------------------------------------------
    #to make sure the user has given process and output arguments together
    invalidShots = []
    if args.output and not args.process:
        print("ERROR: You must provice --process when giving --output")
        sys.exit(1)

    
    elif args.output and args.process:
        videoTimecode = pipeline.get_timecode(args.process[0])[0]
        totalFrames = videoTimecode*24
        invalidShots = soloShots
        shotsInRange = []

        
        for i in shots:
            start, end = i[1].split("-")
            clipped_range = pipeline.clip_frame_range(int(start), int(end), totalFrames)
            targetRange = i[1].split("-")
            if clipped_range is None:
                invalidShots.append(i)
            else:
                clipped_start, clipped_end = clipped_range

                shotsInRange.append((i[0], f"{clipped_start}-{clipped_end}"))
                

        shotsWithTime = pipeline.add_time(shotsInRange)
        print(shotsWithTime)

    
        for counter, shot in enumerate(shotsWithTime, start = 1):
            frame_range = shot[1].split("-")
            shot.append('')

            start_seconds = pipeline.frames_to_seconds(int(frame_range[0]))
            end_seconds = pipeline.frames_to_seconds(int(frame_range[1]) + 1)

            video = pipeline.render_timeFrames(
                args.process[0],
                start_seconds,
                end_seconds,
                counter,
            )
            
            thumbnails = pipeline.thumbnail_creation(video, allThumbnails)
            shot.append(thumbnails[counter-1])
            uri = pipeline.upload_video(client, video)
            
            if uri is None:
                print(f"Failed to upload {video}")
                continue

            try:
                response = client.get(uri + "?fields=transcode.status")        
                response.raise_for_status()
                status = response.json()["transcode"]["status"]
                print(f"{video}: {status}")  
            except Exception as e:
                print(f"Error occurred while fetching video details for {video}: {e}")

        df = pd.DataFrame(shotsWithTime, columns=["Location", "Frame Ranges", "Timecode Ranges", "Thumbnails"])
        with pd.ExcelWriter('output.xlsx', engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="sheet1")
            book = writer.book
            sheet = writer.sheets["sheet1"]
            for i in range(len(thumbnails)):
                sheet.insert_image(f'D{i+2}', thumbnails[i])

    #Create CSV file of the Solo-Frames
    if args.output:
        with open('output.csv', "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(invalidShots)
    pass
    
if __name__ == "__main__":
    main()











