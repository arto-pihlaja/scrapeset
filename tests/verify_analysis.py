import asyncio
import os
from src.analysis import AnalysisCrew
from src.scraper.transcriber import process_video

async def test_youtube_extraction():
    print("Testing YouTube extraction...")
    from src.scraper.transcriber import fetch_youtube_transcript, get_youtube_id
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Never gonna give you up
    yt_id = get_youtube_id(url)
    print(f"YouTube ID: {yt_id}")
    
    result_dict = fetch_youtube_transcript(yt_id)
    if not result_dict:
        print("fetch_youtube_transcript returned None")
    else:
        print(f"fetch_youtube_transcript returned metadata for: {result_dict.get('metadata', {}).get('title')}")

    result = process_video(url)
    print(f"Result length: {len(result)}")
    print(f"Result snippet: {result[:200]}...")
    assert "[Source: YouTube Transcript]" in result

async def test_analysis_pipeline():
    print("Testing analysis pipeline...")
    crew = AnalysisCrew()
    
    # Step 1: Fetch
    url = "https://www.google.com" # Something simple
    fetch_result = crew.run_step("fetch", {"url": url})
    print("Fetch done.")
    assert fetch_result["source_type"] == "webpage"
    
    # Step 2: Summary
    summary_result = crew.run_step("summary", {"content_data": fetch_result})
    print("Summary done.")
    assert "summary" in summary_result["summary"]
    
    # Step 3: Claims
    claims_result = crew.run_step("claims", {"summary_data": summary_result["summary"]})
    print("Claims done.")
    assert "claims" in claims_result
    
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test_youtube_extraction())
    asyncio.run(test_analysis_pipeline())
