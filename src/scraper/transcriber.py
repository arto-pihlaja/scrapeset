import os
import glob
import subprocess
import math
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse, parse_qs
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_youtube_id(url: str) -> Optional[str]:
    """Extracts YouTube ID from URL."""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [None])[0]
    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")
    return None

def fetch_youtube_transcript(video_id: str) -> Optional[dict]:
    """Attempts to fetch existing transcript and metadata from YouTube."""
    try:
        from src.analysis.tools.youtube import YouTubeMetadataTool
        tool = YouTubeMetadataTool()
        # The tool expects a full URL, but we can reconstruct it or modify tool
        url = f"https://www.youtube.com/watch?v={video_id}"
        result = tool._run(url)
        
        if result.get("transcript"):
            return {
                "text": result["transcript"],
                "metadata": {
                    "title": result.get("title"),
                    "channel": result.get("channel"),
                    "description": result.get("description"),
                    "duration": result.get("duration")
                }
            }
        return None
    except Exception as e:
        logger.warning(f"YouTube transcript failed: {e}")
        return None


def extract_metadata_and_subs(url: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Uses yt-dlp to get metadata and check for subtitles.
    Returns (metadata_dict, subtitle_content).
    """
    # Create temp folder for subs
    temp_folder = settings.download_folder
    os.makedirs(temp_folder, exist_ok=True)
    
    # We use a unique ID for the file to avoid collisions
    # But for extracting subs we need to know the output filename
    # yt-dlp naming can be tricky with subs.
    
    ydl_opts = {
        'skip_download': True,
        'writesub': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['en.*','en'], # Prefer English
        'outtmpl': os.path.join(temp_folder, '%(id)s'), # No extension, it appends .en.vtt
        'quiet': True,
    }
    
    if settings.youtube_cookies_path:
        ydl_opts['cookiefile'] = settings.youtube_cookies_path
    
    if settings.ffmpeg_location and settings.ffmpeg_location != "ffmpeg":
         ydl_opts['ffmpeg_location'] = settings.ffmpeg_location

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True) # download=True needed to write subs file even if skip_download is True for video
            
            # Now find the subtitle file
            video_id = info.get('id')
            # Look for likely subtitle files
            potential_files = glob.glob(os.path.join(temp_folder, f"{video_id}*.vtt"))
            
            subtitle_content = None
            if potential_files:
                # Read the first one
                with open(potential_files[0], 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                # Cleanup
                for f in potential_files:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                        
            return info, subtitle_content
        except Exception as e:
            logger.error(f"Metadata/Sub extraction failed: {e}")
            # If extraction failed, we return empty info and None
            return {}, None

def download_audio(url: str) -> str:
    """Downloads audio from a URL using yt-dlp."""
    download_folder = settings.download_folder
    os.makedirs(download_folder, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(download_folder, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    if settings.youtube_cookies_path:
        ydl_opts['cookiefile'] = settings.youtube_cookies_path

    if settings.ffmpeg_location and settings.ffmpeg_location != "ffmpeg":
         ydl_opts['ffmpeg_location'] = settings.ffmpeg_location

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_path = os.path.join(download_folder, f"{info['id']}.mp3")
        return audio_path

def split_audio(audio_path: str, max_size_mb: int = 25) -> List[str]:
    """Splits an audio file into chunks using ffmpeg if it exceeds max_size_mb."""
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return [audio_path]

    logger.info(f"Audio file size ({file_size_mb:.2f}MB) exceeds limit. Splitting...")
    
    chunks_folder = settings.audio_chunks_folder
    os.makedirs(chunks_folder, exist_ok=True)
    
    # Get duration
    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    duration = float(subprocess.check_output(ffprobe_cmd).strip())
    
    # Calculate number of chunks
    num_chunks = math.ceil(file_size_mb / (max_size_mb * 0.9)) # 10% safety margin
    chunk_duration = duration / num_chunks
    
    chunks = []
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        output_path = os.path.join(chunks_folder, f"{base_name}_chunk_{i}.mp3")
        
        ffmpeg_cmd = [
            settings.ffmpeg_location, "-y", "-ss", str(start_time),
            "-t", str(chunk_duration), "-i", audio_path,
            "-acodec", "copy", output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        chunks.append(output_path)
    
    return chunks

def transcribe_audio_file(audio_path: str, api_key: str) -> str:
    """Transcribes an audio file using OpenAI Whisper API."""
    client = OpenAI(api_key=api_key)
    
    chunks = split_audio(audio_path)
    full_transcript = []
    
    try:
        for chunk_path in chunks:
            with open(chunk_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                full_transcript.append(transcript.text)
            
            # Cleanup chunk if it's not the original file
            if chunk_path != audio_path and os.path.exists(chunk_path):
                os.remove(chunk_path)
                
        return " ".join(full_transcript)
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        # Cleanup chunks on failure
        for chunk_path in chunks:
            if chunk_path != audio_path and os.path.exists(chunk_path):
                os.remove(chunk_path)
        raise e

def process_video(url: str, api_key: Optional[str] = None) -> str:
    """Main orchestrator function for video transcription."""
    
    # 1. Check YouTube Transcript & Metadata (Improved version)
    yt_id = get_youtube_id(url)
    if yt_id:
        logger.info(f"Detected YouTube ID: {yt_id}. Checking for existing transcripts and metadata...")
        result = fetch_youtube_transcript(yt_id)
        if result and result.get("text"):
            metadata_str = ""
            meta = result.get("metadata", {})
            if meta.get("title"):
                metadata_str = f"Title: {meta['title']}\nChannel: {meta.get('channel', 'Unknown')}\n\n"
            return f"[Source: YouTube Transcript]\n\n{metadata_str}{result['text']}"
            
     # 2. Check YouTube Subtitles via yt-dlp (Robust fallback for subs)
    # This works without ffmpeg if we just want VTT subs
    if yt_id:
         logger.info("Checking for subtitles via yt-dlp...")
         _, subs = extract_metadata_and_subs(url)
         if subs:
             import re
             # 1. Remove 'o' artifacts before tags (common in some VTT dumps)
             subs = re.sub(r'o(?=<)', '', subs)
             # 2. Remove timestamps <00:00:00.000>
             subs = re.sub(r'<[\d:.]+(>)?', '', subs)
             # 3. Remove other tags like <c>, </c>
             subs = re.sub(r'<[^>]+>', '', subs)
             
             lines = subs.splitlines()
             text_lines = []
             
             for line in lines:
                 if '-->' in line: continue
                 if line.strip() == '' or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'): continue
                 
                 clean_line = line.strip()
                 text_lines.append(clean_line)
             
             # Join and dedup words
             full_text = " ".join(text_lines)
             full_text = re.sub(r'\s+', ' ', full_text).strip()
             
             words = full_text.split()
             deduped_words = [words[0]] if words else []
             for w in words[1:]:
                 if w != deduped_words[-1]:
                     deduped_words.append(w)
             
             clean_text = " ".join(deduped_words)
             
             return f"[Source: YouTube Subtitles (yt-dlp)]\n\n{clean_text}"
    
    # 3. Download Audio & Transcribe (Last Resort)
    # This DOES require ffmpeg
    if not api_key:
        api_key = settings.whisper_api_key or settings.openai_api_key
    
    if not api_key:
        return "Error: No Transcript found and no OpenAI/Whisper API Key provided. Cannot proceed to audio transcription."

    logger.info("Downloading audio for transcription (requires ffmpeg)...")
    audio_path = None
    try:
        audio_path = download_audio(url)
        logger.info(f"Audio downloaded to {audio_path}. Transcribing with OpenAI...")
        
        text = transcribe_audio_file(audio_path, api_key)
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return f"[Source: OpenAI Whisper]\n\n{text}"
            
    except Exception as e:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        return f"Error processing video: {str(e)}"
