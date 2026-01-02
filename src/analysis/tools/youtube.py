"""YouTube metadata and transcript extraction tools, ported from argumentanalyzer."""

import os
import re
import logging
from typing import Any

from crewai.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class YouTubeMetadataTool(BaseTool):
    """Tool to extract metadata and transcript from YouTube videos."""

    name: str = "youtube_metadata"
    description: str = (
        "Extract metadata (title, channel, description, duration) and transcript "
        "from a YouTube video URL. Returns structured data including timestamped transcript."
    )

    def _run(self, url: str) -> dict[str, Any]:
        """Extract YouTube video metadata and transcript."""
        video_id = extract_video_id(url)
        if not video_id:
            return {"error": f"Could not extract video ID from URL: {url}"}

        result = {
            "source_type": "youtube",
            "url": url,
            "video_id": video_id,
            "title": None,
            "channel": None,
            "description": None,
            "duration": None,
            "transcript": None,
            "transcript_with_timestamps": None,
        }

        # Get video metadata using yt-dlp
        from src.config.settings import settings
        cookies_path = settings.youtube_cookies_path
        # Force default if not set in env but exists in downloads
        if not cookies_path:
            default_cookies = "downloads/www.youtube.com_cookies.txt"
            if os.path.exists(default_cookies):
                cookies_path = default_cookies

        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            if cookies_path and os.path.exists(cookies_path):
                ydl_opts["cookiefile"] = cookies_path
                logger.info(f"Using YouTube cookies from {cookies_path}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                result["title"] = info.get("title")
                result["channel"] = info.get("channel") or info.get("uploader")
                result["description"] = info.get("description")
                duration_seconds = info.get("duration")
                if duration_seconds:
                    minutes, seconds = divmod(duration_seconds, 60)
                    hours, minutes = divmod(minutes, 60)
                    if hours:
                        result["duration"] = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        result["duration"] = f"{minutes}:{seconds:02d}"
        except Exception as e:
            result["metadata_error"] = str(e)

        # Get transcript using youtube-transcript-api
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # New API: instantiate and call fetch()
            ytt_api = YouTubeTranscriptApi()
            
            # Pass cookies to the API if available
            # Note: 1.2.3 might handle cookies differently, checking support
            try:
                 # Prefer English, fallback to whatever
                 ts_list = ytt_api.list(video_id)
                 transcript_obj = ts_list.find_transcript(['en'])
                 transcript = transcript_obj.fetch()
            except Exception as e:
                 logger.warning(f"Could not find English transcript: {e}")
                 # Fallback to direct fetch which hopefully finds something
                 transcript = ytt_api.fetch(video_id)

            # Build plain transcript and timestamped version
            plain_parts = []
            timestamped_parts = []

            for entry in transcript:
                # Handle both object (1.2.3+) and dict (legacy)
                if hasattr(entry, 'text'):
                    text = entry.text
                    start = entry.start
                else:
                    text = entry['text']
                    start = entry['start']

                minutes, seconds = divmod(int(start), 60)
                timestamp = f"{minutes}:{seconds:02d}"

                plain_parts.append(text)
                timestamped_parts.append(f"[{timestamp}] {text}")

            result["transcript"] = " ".join(plain_parts)
            result["transcript_with_timestamps"] = "\n".join(timestamped_parts)

        except Exception as e:
            result["transcript_error"] = str(e)

        return result


class WebContentTool(BaseTool):
    """Tool to extract content from web pages."""

    name: str = "web_content"
    description: str = (
        "Extract the main text content from a web page URL. "
        "Returns the page title, main content text, and metadata."
    )

    def _run(self, url: str) -> dict[str, Any]:
        """Extract web page content."""
        import requests
        from bs4 import BeautifulSoup

        result = {
            "source_type": "webpage",
            "url": url,
            "title": None,
            "content": None,
            "author": None,
            "publish_date": None,
        }

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Get title
            title_tag = soup.find("title")
            if title_tag:
                result["title"] = title_tag.get_text().strip()

            # Try to find author
            author_meta = soup.find("meta", {"name": "author"})
            if author_meta:
                result["author"] = author_meta.get("content")

            # Try to find publish date
            date_meta = soup.find("meta", {"property": "article:published_time"})
            if date_meta:
                result["publish_date"] = date_meta.get("content")

            # Remove script, style, nav, footer elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Try to find main content area
            main_content = None
            for selector in ["article", "main", '[role="main"]', ".content", "#content"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.find("body")

            if main_content:
                # Get text content
                paragraphs = main_content.find_all(["p", "h1", "h2", "h3", "h4", "li"])
                text_parts = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Filter out very short fragments
                        text_parts.append(text)

                result["content"] = "\n\n".join(text_parts)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                result["error"] = "Page not found (404). Check the URL or paste content manually."
            elif e.response.status_code == 403:
                result["error"] = "Access denied (403). This site blocks automated access. Paste content manually."
            else:
                result["error"] = f"HTTP error: {e.response.status_code}"
        except requests.exceptions.Timeout:
            result["error"] = "Request timed out. Try again or paste content manually."
        except Exception as e:
            result["error"] = str(e)

        return result


class WebSearchTool(BaseTool):
    """Tool to search the web and scrape results for counterarguments."""

    name: str = "web_search"
    description: str = (
        "Search the web for a given query and return summarized results. "
        "Use this to find counterarguments and opposing viewpoints."
    )

    def _run(self, query: str) -> dict[str, Any]:
        """Search the web and scrape top results."""
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse

        results = {
            "query": query,
            "sources": [],
            "snippets": [],
            "error": None,
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Use DuckDuckGo HTML search (more reliable, no API key needed)
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find search results
            result_links = soup.select(".result__a")
            result_snippets = soup.select(".result__snippet")

            for i, (link, snippet) in enumerate(zip(result_links[:5], result_snippets[:5])):
                href = link.get("href", "")
                title = link.get_text().strip()
                snippet_text = snippet.get_text().strip() if snippet else ""

                # DuckDuckGo wraps URLs, extract actual URL
                if "uddg=" in href:
                    actual_url = urllib.parse.unquote(href.split("uddg=")[-1].split("&")[0])
                else:
                    actual_url = href

                if actual_url and title:
                    results["sources"].append({
                        "title": title,
                        "url": actual_url,
                    })
                    if snippet_text:
                        results["snippets"].append(snippet_text)

            # If we got results, try to scrape the first one for more content
            if results["sources"]:
                try:
                    first_url = results["sources"][0]["url"]
                    page_response = requests.get(first_url, headers=headers, timeout=10)
                    page_soup = BeautifulSoup(page_response.text, "html.parser")

                    # Remove scripts, styles, etc
                    for tag in page_soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()

                    # Get first few paragraphs
                    paragraphs = page_soup.find_all("p")
                    content_parts = []
                    for p in paragraphs[:5]:
                        text = p.get_text().strip()
                        if len(text) > 50:
                            content_parts.append(text)

                    if content_parts:
                        results["first_source_content"] = " ".join(content_parts)[:1500]
                except Exception:
                    pass  # Ignore scraping errors for individual pages

        except Exception as e:
            results["error"] = str(e)

        return results
