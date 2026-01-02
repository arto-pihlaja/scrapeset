import re
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextElement:
    """Represents a text element extracted from a webpage."""
    content: str
    tag: str
    preview: str
    word_count: int
    char_count: int


@dataclass
class ScrapedContent:
    """Container for scraped webpage content."""
    url: str
    title: str
    text_elements: List[TextElement]
    total_text_length: int
    success: bool
    error_message: Optional[str] = None


class WebScraper:
    """Web scraper for extracting text content from URLs using Trafilatura and Playwright."""

    def __init__(self):
        # We still keep a session for consistency or simple checks, 
        # though trafilatura handles its own fetching usually.
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.user_agent,
        })

    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        return url

    def _create_text_elements_from_text(self, text: str) -> List[TextElement]:
        """Convert a block of text into a list of TextElements with robust splitting."""
        elements = []
        if not text:
            return elements

        # Step 1: Initial split by double newlines
        initial_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Step 2: If we only got one huge block, try single newline
        if len(initial_paragraphs) <= 1 and len(text) > 1000:
            initial_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        # Step 3: Handle giant blocks that missed newlines
        processed_paragraphs = []
        max_chunk_chars = 2000
        for p in initial_paragraphs:
            if len(p) > max_chunk_chars:
                # Divide into smaller chunks roughly at word boundaries
                current_p = p
                while len(current_p) > max_chunk_chars:
                    split_idx = current_p.rfind(' ', 0, max_chunk_chars)
                    if split_idx == -1: split_idx = max_chunk_chars
                    processed_paragraphs.append(current_p[:split_idx].strip())
                    current_p = current_p[split_idx:].strip()
                if current_p:
                    processed_paragraphs.append(current_p)
            else:
                processed_paragraphs.append(p)

        # Step 4: Create elements with filtering
        for p in processed_paragraphs:
            words = p.split()
            
            # Substantial enough?
            if len(words) < 5 and len(p) < 20: 
                continue

            preview = ' '.join(words[:settings.text_preview_words])
            if len(words) > settings.text_preview_words:
                preview += "..."

            elements.append(TextElement(
                content=p,
                tag='p', 
                preview=preview,
                word_count=len(words),
                char_count=len(p)
            ))
        
        return elements

    def _scrape_fallback(self, html_content: str) -> str:
        """Fallback extraction logic using BeautifulSoup when Trafilatura fails."""
        logger.info("Using BeautifulSoup fallback extraction")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try to find main content areas
        content_area = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find(id=re.compile(r'content|main|wrapper', re.I)) or
            soup.find(class_=re.compile(r'content|main|article', re.I)) or
            soup.body
        )
        
        if not content_area:
            return ""

        # Remove noise
        for tag in content_area.select('script, style, nav, footer, header, aside, .sidebar, .menu, .ads'):
            tag.decompose()

        # Extract text from structural elements
        text_blocks = []
        for tag in content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'div']):
            # For divs, only take if they don't have children of the same types to avoid duplication
            if tag.name == 'div' and tag.find(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'div']):
                continue
                
            block_text = tag.get_text().strip()
            # Basic sanity check for content-like text
            if len(block_text) > 30 or (tag.name.startswith('h') and len(block_text) > 5):
                # Avoid duplicates that might occur due to nested structures if div check missed some
                if not text_blocks or block_text != text_blocks[-1]:
                    text_blocks.append(block_text)
        
        return '\n\n'.join(text_blocks)

    def _scrape_dynamic(self, url: str) -> str:
        """Use Playwright to render the page and extract HTML."""
        logger.info(f"Scraping dynamic content from {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.playwright_headless)
            page = browser.new_page()
            try:
                page.goto(url, timeout=settings.playwright_timeout + 5000)
                # Wait for network idle or timeout
                try:
                    page.wait_for_load_state("networkidle", timeout=settings.playwright_timeout)
                except Exception:
                    logger.warning("Network idle timeout, proceeding with current content.")
                
                content = page.content()
            finally:
                browser.close()
        return content

    def scrape(self, url: str, dynamic: bool = False) -> ScrapedContent:
        """
        Scrape text content from a URL.
        
        Args:
            url: The URL to scrape
            dynamic: Whether to use Playwright for dynamic content
        """
        try:
            url = self._validate_url(url)
            logger.info(f"Starting scrape of: {url} (Dynamic: {dynamic})")

            html_content = None
            downloaded = None

            if dynamic or settings.use_dynamic_scraping:
                try:
                    html_content = self._scrape_dynamic(url)
                except Exception as e:
                    logger.error(f"Dynamic scraping failed: {e}")
                    # Fallback might be handled by caller or we just fail
                    raise e
            else:
                # Check for video URL first
                from src.scraper.transcriber import get_youtube_id, process_video
                if get_youtube_id(url):
                    logger.info(f"Detected video URL: {url}. Attempting transcription...")
                    try:
                        transcript = process_video(url, api_key=settings.openai_api_key)
                        
                        # Create elements from transcript
                        text_elements = self._create_text_elements_from_text(transcript)
                        total_length = sum(elem.char_count for elem in text_elements)
                        
                        return ScrapedContent(
                            url=url,
                            title=f"Video Transcript: {url}", # We could try to fetch title via yt-dlp metadata in process_video but simple for now
                            text_elements=text_elements,
                            total_text_length=total_length,
                            success=True
                        )
                    except Exception as e:
                        logger.error(f"Video transcription failed: {e}")
                        # Fallback to normal scraping? Or raise?
                        # If it's a YouTube video, normal scraping is useless.
                        raise e

                # Use trafilatura's fetcher
                downloaded = trafilatura.fetch_url(url)
                if downloaded is None:
                     # Try requests as fallback if trafilatura fetch fails (sometimes internal headers issues)
                     resp = self.session.get(url, timeout=settings.request_timeout)
                     resp.raise_for_status()
                     downloaded = resp.text

            # Extract text
            # If we have html_content (dynamic), use that. Else use downloaded.
            content_source = html_content if html_content else downloaded
            
            if not content_source:
                 raise ValueError("Could not fetch content from URL")

            # Extract full text
            text = trafilatura.extract(
                content_source, 
                favor_recall=settings.favor_recall,
                include_tables=settings.include_tables
            )

            if not text:
                logger.warning("Trafilatura extracted no text.")
                text = ""

            # Check for suspicious extraction result (too small compared to HTML size)
            # Heuristic: if text is < 5KB AND HTML is > 50KB, try fallback
            if len(text) < 5000 and len(content_source) > 50000:
                logger.info(f"Trafilatura extraction small ({len(text)} bytes). Trying fallback...")
                fallback_text = self._scrape_fallback(content_source)
                if len(fallback_text) > len(text) * 2:
                    logger.info(f"Fallback extracted significantly more content: {len(fallback_text)} bytes")
                    text = fallback_text

            # Create text elements
            text_elements = self._create_text_elements_from_text(text)
            
            # Try to get title
            # Trafilatura handles metadata extraction too but `extract` just gives text.
            # We can use `bare_extraction` to get metadata, or parsing via lxml.
            # For simplicity, extract title from HTML or requests if possible.
            # `trafilatura` doesn't easily give title in `extract`.
            # We'll do a quick pass or reuse requests title logic which is robust enough OR use trafilatura metadata.
            # bare_extraction returns a dict.
            # bare_extraction returns a Document object in latest trafilatura versions
            bare = trafilatura.bare_extraction(content_source, favor_recall=settings.favor_recall, include_tables=settings.include_tables)
            if bare:
                title = getattr(bare, 'title', None)
                if not title:
                    title = "Untitled"
            else:
                title = "Untitled"

            total_text_length = sum(elem.char_count for elem in text_elements)

            logger.info(f"Successfully scraped {len(text_elements)} text elements "
                       f"({total_text_length} total characters) from {url}")

            return ScrapedContent(
                url=url,
                title=title,
                text_elements=text_elements,
                total_text_length=total_text_length,
                success=True
            )

        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                url=url,
                title="",
                text_elements=[],
                total_text_length=0,
                success=False,
                error_message=error_msg
            )