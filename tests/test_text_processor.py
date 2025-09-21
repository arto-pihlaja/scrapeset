"""Tests for the text processor module."""

import pytest
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from src.text import TextProcessor


class TestTextProcessor:
    """Test cases for the TextProcessor class."""

    def test_clean_text(self):
        """Test text cleaning functionality."""
        processor = TextProcessor()

        # Test whitespace normalization
        text = "This   has    excessive     whitespace"
        cleaned = processor.clean_text(text)
        assert cleaned == "This has excessive whitespace"

        # Test special character removal
        text = "Text with @#$%^&* special chars"
        cleaned = processor.clean_text(text)
        assert "@#$%^&*" not in cleaned
        assert "Text with" in cleaned
        assert "special chars" in cleaned

        # Test punctuation preservation
        text = "Keep this! And this? Yes, please."
        cleaned = processor.clean_text(text)
        assert "!" in cleaned
        assert "?" in cleaned
        assert "," in cleaned
        assert "." in cleaned

    def test_token_counting(self):
        """Test token counting functionality."""
        processor = TextProcessor()

        # Test basic token counting
        text = "This is a simple test"
        token_count = processor.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_create_chunks_small_text(self):
        """Test chunking with text smaller than chunk size."""
        processor = TextProcessor()

        text = "This is a short text."
        chunks = processor.create_chunks(text, "https://example.com", "Test Title")

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].source_url == "https://example.com"
        assert chunks[0].source_title == "Test Title"
        assert chunks[0].chunk_index == 0

    def test_create_chunks_large_text(self):
        """Test chunking with text larger than chunk size."""
        processor = TextProcessor()

        # Create a large text that will need chunking
        large_text = "This is a sentence. " * 100  # Creates a large text
        chunks = processor.create_chunks(
            large_text,
            "https://example.com",
            "Test Title",
            chunk_size=200,  # Small chunk size for testing
            chunk_overlap=50
        )

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 250  # Allow some flexibility for sentence boundaries
            assert chunk.source_url == "https://example.com"
            assert chunk.source_title == "Test Title"
            assert isinstance(chunk.chunk_index, int)
            assert chunk.token_count > 0