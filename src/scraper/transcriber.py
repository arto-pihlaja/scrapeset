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

def fetch_youtube_transcript(video_id: str) -> Optional[str]:
    """Attempts to fetch existing transcript from YouTube."""
    try:
        # Pass cookies if available
        cookies_file = settings.youtube_cookies_path
        
        # list_transcripts returns a TranscriptList object which is iterable
        # Note: list_transcripts does accept cookies in newer versions, 
        # but if not, we rely on the environment or netrc. 
        # Actually youtube_transcript_api supports checking cookies.txt format?
        # It supports `cookies` argument in `get_transcript` and `list_transcripts`.
        kwargs = {}
        if cookies_file and os.path.exists(cookies_file):
             kwargs['cookies'] = cookies_file

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, **kwargs)
        
        # Try to find a transcript (manual or auto-generated)
        # We prioritize english manual, then english auto, then whatever is available
        transcript = None
        
        try:
           transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            except NoTranscriptFound:
                # Fallback to any available transcript
                for t in transcript_list:
                    transcript = t
                    break
                    
        if not transcript:
            return None
            
        fetched = transcript.fetch()
        full_text = " ".join([item['text'] for item in fetched])
        return full_text
    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
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

# ... (download_audio, split_audio, transcribe_audio_file omitted - kept as is) ...

def process_video(url: str, api_key: Optional[str] = None) -> str:
    """Main orchestrator function for video transcription."""
    
    # 1. Check YouTube Transcript API (Fastest, no auth usually needed for public)
    yt_id = get_youtube_id(url)
    if yt_id:
        logger.info(f"Detected YouTube ID: {yt_id}. Checking for existing transcripts via API...")
        text = fetch_youtube_transcript(yt_id)
        if text:
            return f"[Source: YouTube Transcript]\n\n{text}"
            
     # 2. Check YouTube Subtitles via yt-dlp (Robust, handles cookies well)
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
