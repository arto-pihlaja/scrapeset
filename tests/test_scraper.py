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

    def test_text_element_creation(self):
        """Test text element creation from raw text."""
        scraper = WebScraper()
        
        # Test basic text split
        raw_text = "Paragraph 1\n\nParagraph 2\n\nP3"
        elements = scraper._create_text_elements_from_text(raw_text)
        
        # Note: P3 might be filtered out if it's too short, depending on settings.
        # Assuming defaults: MIN_TEXT_LENGTH=300? No, let's check settings.
        # Actually in _create_text_elements_from_text I added a hard check:
        # if len(words) < 5: continue
        
        text_long = "This is a sentence with enough words to be kept I hope."
        text_short = "Short."
        
        elements = scraper._create_text_elements_from_text(f"{text_long}\n\n{text_short}")
        
        # Should have 1 element (the long one)
        assert len(elements) == 1
        assert elements[0].content == text_long
        
        # Test preview generation
        text_very_long = "word " * 100
        elements = scraper._create_text_elements_from_text(text_very_long)
        assert elements[0].preview.endswith("...")