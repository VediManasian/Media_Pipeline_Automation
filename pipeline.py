import ffmpeg
import logging
from fractions import Fraction

logger = logging.getLogger(__name__)

# Parses Baselight metadata and maps shot directories to their frame numbers,
# combining frames from duplicate directories.
def load_baselight(data):
    result = {}
    line_number = 0
    for line in data:
        line_number += 1
        parts = line.split()

        if not parts:
            continue

        if len(parts) < 2:
            raise ValueError(
                f"Missing frames on line {line_number}"
            )

        directory = parts[0]
        frames = parts[1:]

        for frame in frames:
            if not frame.isascii() or not frame.isdecimal():
                raise ValueError(
                    f"Invalid frame on line {line_number}"
                )

        if directory in result:
            result[directory].extend(frames)
        else:
            result[directory] = frames
    return result

# Parses Xytech metadata to extract the workorder number
# and its associated production directories.
def load_xytech(data):
    result = {}
    workorder = None

    for line in data:
        line = line.strip()
        if not line:
            continue

        if "workorder" in line.lower():
            parts = line.lower().split("workorder")
            workorder = parts[1].strip()

            if workorder == "":
                raise ValueError("Missing workorder number")

            result[workorder] = []
        elif line.startswith("/"):
            if workorder is None:
                raise ValueError("Missing workorder")

            result[workorder].append(line)

        if (len(result) == 0):
            raise ValueError("Missing workorder")

    return result

# Matches Baselight shot directories with their corresponding Xytech
# production directories and associates them with their frame numbers.
def comparison_algorithm(baselight, xytech):
    Dict = {}
    for location, frames in baselight.items():
        modifiedLocation = location.split("/", 2)[2:]
        for workorder, directories in xytech.items():
            for i in directories:
                if i.endswith(modifiedLocation[0]):
                    if i in Dict:
                        Dict[i].extend(frames)
                    else:
                        Dict[i] = frames
    return Dict

# Removes duplicate frames, sorts them numerically, and groups
# consecutive frame numbers into ranges while preserving isolated frames.
def frame_ranges(data):
    result = []
    for location, frames in data.items():
        frames = sorted(set(int(frame) for frame in frames))
        if not frames: continue
        start = frames[0]
        end = frames[0]
        for frame in frames[1:]:
            if frame == end + 1:
                end = frame
            else:
                frameBlock = str(start) if start == end else f"{start}-{end}"
                result.append((location, frameBlock))
                start = frame
                end = frame
        frameBlock = str(start) if start == end else f"{start}-{end}"
        result.append((location, frameBlock))
    return result

# Separates multi-frame shot ranges from isolated single frames,
# returning each category in a separate list.
def seperate_frames(data):
    shots = []
    soloFrames = []
    for i in data:
        if len(i[1].split("-")) == 1:
            soloFrames.append(i)
        else:
            shots.append(i)
    return (shots, soloFrames)

# Clips a given frame range to ensure it falls within the valid bounds of the video.
def clip_frame_range(start, end, total_frames):
    if start < 0 or end < start:
        raise ValueError("Invalid frame range")
    if total_frames <= 0 or start >= total_frames:
        return None
    return start, min(end, total_frames - 1)

# Converts a timecode in HH:MM:SS:FF format into elapsed seconds
# using the specified frame rate, rounded to two decimal places.
def timecode_to_seconds(timecode, fps=24):
    time = timecode.split(":")
    hours = int(time[0])
    minutes = int(time[1])
    seconds = int(time[2])
    frames = int(time[3])

    total_seconds = round(hours * 3600 + minutes * 60 + seconds + (frames / fps), 2)
    return total_seconds

# Converts an absolute frame number into HH:MM:SS:FF timecode format
def frames_to_timecode(frame, fps=24):
    frame = int(frame)
    hour = frame // (3600 * fps)
    frame %= (fps * 3600)
    minutes = frame // (fps * 60)
    frame %= (fps * 60)
    seconds = frame // fps
    frames = frame % fps
    result = f"{hour:02}:{minutes:02}:{seconds:02}:{frames:02}"
    return result

def seconds_to_timecode(seconds, fps=24):
    total_frames = int(round(seconds * fps))
    return frames_to_timecode(total_frames, fps)

def frames_to_seconds(frame, fps=24):
    return frame / fps

# Retrieves the video's duration in seconds using FFmpeg metadata
# and returns it as a single-element list.
def get_timecode(targetVideo):
    info = ffmpeg.probe(targetVideo)
    duration = float(info['format']['duration'])
    return [duration]

# Adds starting and ending timecodes to each shot while retaining
# its original production directory and frame range.
def add_time(shotsList):
    result = []
    for i in range(len(shotsList)):
        targetRange = shotsList[i][1].split("-")
        result.append([shotsList[i][0], shotsList[i][1], f"{frames_to_timecode(int(targetRange[0]))}-{frames_to_timecode(int(targetRange[1]))}"])
    return result

# Extracts a video segment between the specified start and end times,
# encodes it as an MP4 file, and returns the generated file path.
def render_timeFrames(video, startTime, endTime, iterator):
    output = f'{video[:-4]}_shot{iterator}.mp4'
    probe = ffmpeg.probe(video)
    video_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    width = video_stream['width']
    height = video_stream['height']
    framerate = float(Fraction(video_stream["r_frame_rate"]))
    main = ffmpeg.input(video, ss=startTime, to=endTime)
    black = ffmpeg.input(f'color=c=black:s={width}x{height}:d=1:r={framerate}', f='lavfi')
    silence = ffmpeg.input(f'anullsrc=channel_layout=stereo:sample_rate=48000', f='lavfi', t=1)
    #----------------------------------------------------------------------------------------

    (
        ffmpeg
        .concat(main.video, main.audio, black.video, silence.audio, v=1, a=1)
        .output(output, vcodec='libx264', acodec='aac', movflags="+faststart")
        .overwrite_output()
        .run()
    )
    return output

# Generates a 96x74 JPEG thumbnail from the beginning of a video
# and appends its file path to the collection of generated thumbnails.
def thumbnail_creation(video, allThumbnails):
    output = f"{video[:-4]}_thumbnail.jpg"
    duration = get_timecode(video)[0]
    time = duration / 2
    (
        ffmpeg
        .input(video, ss=0)
        .output(output, vframes=1, vf="scale=96:74", update=1)
        .overwrite_output()
        .run()
    )
    allThumbnails.append(output)
    return allThumbnails

def upload_video(client, video):
    try:
        uri = client.upload(
            video,
            data={
                "name": video,
                "description": ""
            }
        )
        
        return uri

    except Exception:
        logger.exception("Failed to upload %s", video)
        return None