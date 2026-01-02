import asyncio
import os
import sys
from src.analysis.tools.youtube import YouTubeMetadataTool
from youtube_transcript_api import YouTubeTranscriptApi

def test_direct_api():
    video_id = "dQw4w9WgXcQ"
    print(f"Testing direct YouTubeTranscriptApi for {video_id}...")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        print(f"YouTubeTranscriptApi class: {YouTubeTranscriptApi}")
        
        # Check for various common names
        for attr in ['list', 'list_transcripts', 'get_transcript', 'fetch']:
            print(f"Has {attr}: {hasattr(YouTubeTranscriptApi, attr)}")
            
        ytt = YouTubeTranscriptApi()
        for attr in ['list', 'list_transcripts', 'get_transcript', 'fetch']:
            print(f"Instance has {attr}: {hasattr(ytt, attr)}")

        try:
            ts = ytt.list(video_id)
            print("ytt.list(video_id) worked!")
            transcript = ts.find_transcript(['en']).fetch()
            print(f"Transcript type: {type(transcript)}")
            if transcript:
                entry = transcript[0]
                print(f"Entry type: {type(entry)}")
                print(f"Entry dir: {dir(entry)}")
                try:
                    print(f"Entry['text']: {entry['text']}")
                except:
                    print("Entry is NOT subscriptable")
                
                # Check attributes
                for attr in ['text', 'start', 'duration']:
                    print(f"Entry.{attr}: {getattr(entry, attr, 'N/A')}")
                    
        except Exception as e:
            print(f"ytt.list(video_id) or fetch failed: {e}")

    except Exception as e:
        print(f"Direct API test failed: {e}")

def test_tool():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"Testing YouTubeMetadataTool for {url}...")
    tool = YouTubeMetadataTool()
    result = tool._run(url)
    if result.get("transcript"):
        print("Tool successfully got transcript.")
        print(f"Snippet: {result['transcript'][:100]}")
    else:
        print(f"Tool failed to get transcript. Error: {result.get('transcript_error')}")
        print(f"Metadata: {result.get('title')}, {result.get('channel')}")

if __name__ == "__main__":
    test_direct_api()
    print("-" * 20)
    test_tool()
