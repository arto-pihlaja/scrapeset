import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.transcriber import download_audio, split_audio, transcribe_audio_file, process_video

@patch('src.scraper.transcriber.yt_dlp.YoutubeDL')
def test_download_audio(mock_ydl):
    mock_instance = mock_ydl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {'id': 'test_id'}
    
    with patch('os.makedirs'):
        path = download_audio("https://youtube.com/watch?v=123")
        assert "test_id.mp3" in path

@patch('src.scraper.transcriber.subprocess.check_output')
@patch('src.scraper.transcriber.subprocess.run')
@patch('os.path.getsize')
def test_split_audio_no_split(mock_getsize, mock_run, mock_check):
    mock_getsize.return_value = 10 * 1024 * 1024 # 10MB
    chunks = split_audio("fake_path.mp3")
    assert chunks == ["fake_path.mp3"]
    mock_run.assert_not_called()

@patch('src.scraper.transcriber.subprocess.check_output')
@patch('src.scraper.transcriber.subprocess.run')
@patch('os.path.getsize')
@patch('os.makedirs')
def test_split_audio_with_split(mock_makedirs, mock_getsize, mock_run, mock_check):
    mock_getsize.return_value = 50 * 1024 * 1024 # 50MB
    mock_check.return_value = b"100.0" # 100 seconds
    
    chunks = split_audio("fake_path.mp3")
    assert len(chunks) == 3 # 50 / (25 * 0.9) = 2.22 -> 3 chunks
    assert mock_run.call_count == 3

@patch('src.scraper.transcriber.OpenAI')
@patch('src.scraper.transcriber.split_audio')
@patch('builtins.open', new_callable=MagicMock)
def test_transcribe_audio_file(mock_open, mock_split, mock_openai):
    mock_split.return_value = ["chunk1.mp3", "chunk2.mp3"]
    mock_client = mock_openai.return_value
    mock_client.audio.transcriptions.create.return_value.text = "chunk text"
    
    with patch('os.path.exists', return_value=True), patch('os.remove'):
        result = transcribe_audio_file("fake_path.mp3", "fake_key")
        assert result == "chunk text chunk text"

if __name__ == "__main__":
    try:
        test_download_audio()
        print("test_download_audio passed")
        test_split_audio_no_split()
        print("test_split_audio_no_split passed")
        test_split_audio_with_split()
        print("test_split_audio_with_split passed")
        test_transcribe_audio_file()
        print("test_transcribe_audio_file passed")
        print("\nAll tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
