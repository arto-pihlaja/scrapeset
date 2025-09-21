"""Web scraper for extracting text content from URLs."""

import re
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    """Web scraper for extracting text content from URLs."""

    def __init__(self):
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=settings.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        return session

    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        return url

    def _extract_text_elements(self, soup: BeautifulSoup) -> List[TextElement]:
        """Extract text elements from BeautifulSoup object."""
        text_elements = []

        # Define tags that typically contain meaningful text content
        content_tags = ['p', 'div', 'article', 'section', 'main', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']

        for tag_name in content_tags:
            elements = soup.find_all(tag_name)

            for element in elements:
                text = self._extract_clean_text(element)
                if len(text) >= settings.min_text_length:
                    # Generate preview (first N words)
                    words = text.split()
                    preview = ' '.join(words[:settings.text_preview_words])
                    if len(words) > settings.text_preview_words:
                        preview += "..."

                    text_element = TextElement(
                        content=text,
                        tag=tag_name,
                        preview=preview,
                        word_count=len(words),
                        char_count=len(text)
                    )
                    text_elements.append(text_element)

        return text_elements

    def _extract_clean_text(self, element: Tag) -> str:
        """Extract and clean text from a BeautifulSoup element."""
        # Remove script and style elements
        for script in element.find_all(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()

        # Get text and clean it
        text = element.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)

        # Fallback to h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)

        return "Untitled"

    def scrape(self, url: str) -> ScrapedContent:
        """Scrape text content from a URL.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedContent object with extracted text elements
        """
        try:
            # Validate URL
            url = self._validate_url(url)
            logger.info(f"Starting scrape of: {url}")

            # Fetch the page
            response = self.session.get(url, timeout=settings.request_timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract content
            title = self._extract_title(soup)
            text_elements = self._extract_text_elements(soup)
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

        except requests.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                url=url,
                title="",
                text_elements=[],
                total_text_length=0,
                success=False,
                error_message=error_msg
            )

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                url=url,
                title="",
                text_elements=[],
                total_text_length=0,
                success=False,
                error_message=error_msg
            )