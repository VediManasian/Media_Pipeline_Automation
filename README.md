# Media Pipeline Automation

A Python command-line tool for processing Baselight and Xytech
production metadata, grouping frame ranges, and generating
media reports.

## Features

- Parse and validate Baselight frame metadata.
- Associate shot paths with Xytech production directories.
- Group consecutive frames and identify isolated frames.
- Convert frame numbers to timecodes.
- Render video segments and generate thumbnails using FFmpeg.
- Export CSV and Excel reports.
- Upload rendered clips to Vimeo.

## Setup

1. Install Python and FFmpeg, including ffprobe.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements-dev.txt
   ```

4. Copy `.env.example` to `.env` and fill in your credentials.

## Usage

Process the sample metadata:

```powershell
python main.py --baselight examples/baselight.txt --xytech examples/xytech.txt
```

Process a local video and upload the generated clips:

```powershell
python main.py --baselight examples/baselight.txt --xytech examples/xytech.txt --process sample.mp4 --output
```

The video workflow performs real Vimeo uploads.

## Testing

```powershell
python -m pytest --cov=pipeline --cov-branch --cov-report=term-missing
```

Tests cover metadata parsing, frame grouping, frame bounds,
timecode conversion, and mocked Vimeo upload success and failure.

The mocked upload tests do not contact Vimeo.

## Current limitations

- Timecode calculations assume 24 fps.
- Metadata processing requires MongoDB.
- Each run replaces the baselight and xytech collections in
  the dedicated media_pipeline_demo database.
- The current renderer expects a video with an audio stream.
- Existing unit tests do not verify the complete video workflow.