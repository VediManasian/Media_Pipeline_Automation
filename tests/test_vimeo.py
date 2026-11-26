from unittest.mock import Mock
from pipeline import upload_video

def test_successful_upload():
    mock_client = Mock()
    mock_client.upload.return_value = "https://vimeo.com/123456789"

    result = upload_video(mock_client, "TestVideo.mp4")
    assert result == "https://vimeo.com/123456789"

    mock_client.upload.assert_called_once_with(
        "TestVideo.mp4",
        data={
            "name": "TestVideo.mp4",
            "description": ""
        }
    )

def test_failed_upload():
    mock_client = Mock()
    mock_client.upload.side_effect = Exception("Upload failed")

    result = upload_video(mock_client, "TestVideo.mp4")
    assert result is None

def test_network_timeout():
    mock_client = Mock()
    mock_client.upload.side_effect = TimeoutError("Network timeout")

    result = upload_video(mock_client, "TestVideo.mp4")
    assert result is None

def test_continue_after_failed_upload():
    mock_client = Mock()
    mock_client.upload.side_effect = [Exception("Network Unavailable"), "https://vimeo.com/987654321"]

    first = upload_video(mock_client, "TestVideo1.mp4")
    second = upload_video(mock_client, "TestVideo2.mp4")
    assert first is None
    assert second == "https://vimeo.com/987654321"

    assert mock_client.upload.call_count == 2

