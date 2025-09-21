"""Tests for the web scraper module."""

import pytest
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from src.scraper import WebScraper


class TestWebScraper:
    """Test cases for the WebScraper class."""

    def test_url_validation(self):
        """Test URL validation functionality."""
        scraper = WebScraper()

        # Test valid URLs
        assert scraper._validate_url("https://example.com") == "https://example.com"
        assert scraper._validate_url("http://example.com") == "http://example.com"
        assert scraper._validate_url("example.com") == "https://example.com"

        # Test invalid URLs
        with pytest.raises(ValueError):
            scraper._validate_url("")

    def test_session_creation(self):
        """Test that session is created properly."""
        scraper = WebScraper()
        assert scraper.session is not None
        assert "User-Agent" in scraper.session.headers

    def test_extract_clean_text(self):
        """Test text extraction and cleaning."""
        from bs4 import BeautifulSoup

        scraper = WebScraper()

        # Test basic text extraction
        html = "<p>This is a test paragraph.</p>"
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('p')
        text = scraper._extract_clean_text(element)
        assert text == "This is a test paragraph."

        # Test script/style removal
        html = """
        <div>
            <p>Good content</p>
            <script>alert('bad')</script>
            <style>body { color: red; }</style>
            <p>More good content</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('div')
        text = scraper._extract_clean_text(element)
        assert "Good content" in text
        assert "More good content" in text
        assert "alert" not in text
        assert "color: red" not in text