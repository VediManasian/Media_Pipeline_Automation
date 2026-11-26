import pytest
from io import StringIO
from textwrap import dedent
import pipeline

#Testing Loading of Baselight Metadata
@pytest.mark.parametrize("input_data, expected_output", [
    ("/shot001 100 101 102", { "/shot001": ["100", "101", "102"] }),
    ("/shot001 100", { "/shot001": ["100"] }),
    ("shot001 100 101 102", { "shot001": ["100", "101", "102"] }),
    ("/shot1 1 2 3\n/shot2 4 5", { "/shot1": ["1", "2", "3"], "/shot2": ["4", "5"] }),
    ("/shot1 1 2\n/shot1 3 4", {"/shot1": ["1", "2", "3", "4"] }),
    ("", {}),
])
def test_load_baselight(input_data, expected_output):
    assert pipeline.load_baselight(StringIO(input_data)) == expected_output

def test_invalid_frame():
    data = StringIO("/shot1 1 ABC 3")

    with pytest.raises(ValueError, match="Invalid frame"):
        pipeline.load_baselight(data)


def test_missing_frames():
    data = StringIO("/shot1")

    with pytest.raises(ValueError, match="Missing frames"):
        pipeline.load_baselight(data)

#Testing Loading of Xytech Metadata
@pytest.mark.parametrize("input_data, expected_output", [
    ("Xytech Workorder 1169", {"1169": []}),
    ("Xytech Workorder 1169\n/shot001 100 101 102", {"1169": ["/shot001 100 101 102"]}),
    ("Xytech Workorder 1169\nshot001 100 101 102", {"1169": []}),
    ("Xytech Workorder 1169\n/shot001 100 101 102\n/hpsans12/production/dogman/reel1/VFX/Hydraulx\n/hpsans13/production/dogman/reel1/VFX/Framestore", {"1169": ["/shot001 100 101 102", "/hpsans12/production/dogman/reel1/VFX/Hydraulx", "/hpsans13/production/dogman/reel1/VFX/Framestore"]})
])
def test_load_xytech(input_data, expected_output):
    assert pipeline.load_xytech(StringIO(input_data)) == expected_output

def test_missing_workorder():
    data = StringIO("/project/shot1")

    with pytest.raises(ValueError, match="Missing workorder"):
        pipeline.load_xytech(data)

#Testing Frame Ranges
@pytest.mark.parametrize("input_data, expected_output", [
    (
        {
            "/shot001": ["100", "101", "102", "104", "105"],
            "/shot002": ["200", "201", "203"]
        },
        [
            ("/shot001", "100-102"),
            ("/shot001", "104-105"),
            ("/shot002", "200-201"),
            ("/shot002", "203")
        ]
    )
])
def test_frame_ranges(input_data, expected_output):
    assert pipeline.frame_ranges(input_data) == expected_output

@pytest.mark.parametrize("input_start, input_end, total_frames, expected_output", [
    (-1, 100, 200, ValueError),
    (100, 50, 200, ValueError),
    (100, 150, 1, None),
    (100, 150, -1, None),
    (1,1,1, None),
    (100, 150, 200, (100, 150)),
    (100, 250, 200, (100, 199))  
])
def test_clip_frame_range(input_start, input_end, total_frames, expected_output):
    if expected_output is ValueError:
        with pytest.raises(ValueError):
            pipeline.clip_frame_range(input_start, input_end, total_frames)
    else:
        assert pipeline.clip_frame_range(input_start, input_end, total_frames) == expected_output

#Testing Timecode Conversion
@pytest.mark.parametrize("input_frame, expected_timecode", [
    (0, "00:00:00:00"),
    (1, "00:00:00:01"),
    (23, "00:00:00:23"),
    (24, "00:00:01:00"),
    (25, "00:00:01:01"),
    (1440, "00:01:00:00"),
    (86400, "01:00:00:00"),
])
def test_frames_to_timecode(input_frame,  expected_timecode):
    assert pipeline.frames_to_timecode(input_frame) == expected_timecode

@pytest.mark.parametrize("input_timecode, expected_frame", [
    ("00:00:00:00", 0),
    ("00:00:01:00", 1),
    ("00:01:00:00", 60),
    ("01:00:00:00", 3600),
])
def test_timecode_to_seconds(input_timecode, expected_frame):
    assert pipeline.timecode_to_seconds(input_timecode, 24) == expected_frame




