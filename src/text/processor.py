"""Text processing utilities for chunking and cleaning text content."""

import re
import uuid
from dataclasses import dataclass
from typing import List, Optional

import tiktoken

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    id: str
    content: str
    source_url: str
    source_title: str
    chunk_index: int
    token_count: int
    char_count: int
    metadata: dict


class TextProcessor:
    """Processes text for embedding and storage in vector database."""

    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'""]', ' ', text)

        # Remove excessive punctuation
        text = re.sub(r'[.,!?;:]{2,}', '.', text)

        # Clean up spacing around punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1 \2', text)

        # Trim and normalize
        text = text.strip()

        return text

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.tokenizer.encode(text))

    def create_chunks(
        self,
        text: str,
        source_url: str,
        source_title: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[TextChunk]:
        """Split text into chunks suitable for embedding.

        Args:
            text: Text to chunk
            source_url: URL of the source document
            source_title: Title of the source document
            chunk_size: Maximum chunk size in characters (uses config default if None)
            chunk_overlap: Overlap between chunks in characters (uses config default if None)

        Returns:
            List of TextChunk objects
        """
        if chunk_size is None:
            chunk_size = settings.chunk_size
        if chunk_overlap is None:
            chunk_overlap = settings.chunk_overlap

        # Clean the text first
        cleaned_text = self.clean_text(text)

        if len(cleaned_text) <= chunk_size:
            # Text is small enough to be a single chunk
            chunk_id = str(uuid.uuid4())
            chunk = TextChunk(
                id=chunk_id,
                content=cleaned_text,
                source_url=source_url,
                source_title=source_title,
                chunk_index=0,
                token_count=self.count_tokens(cleaned_text),
                char_count=len(cleaned_text),
                metadata={
                    "chunk_id": chunk_id,
                    "source_url": source_url,
                    "source_title": source_title,
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            )
            return [chunk]

        # Split text into overlapping chunks
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(cleaned_text):
            # Calculate end position
            end = start + chunk_size

            # If this is not the last chunk, try to break at a sentence or word boundary
            if end < len(cleaned_text):
                # Look for sentence boundaries first (within the last 200 chars)
                sentence_break = cleaned_text.rfind('.', max(start, end - 200), end)
                if sentence_break > start:
                    end = sentence_break + 1

                # If no sentence boundary, look for word boundaries
                elif end < len(cleaned_text):
                    word_break = cleaned_text.rfind(' ', max(start, end - 100), end)
                    if word_break > start:
                        end = word_break

            # Extract chunk content
            chunk_content = cleaned_text[start:end].strip()

            if chunk_content:  # Only create non-empty chunks
                chunk_id = str(uuid.uuid4())
                chunk = TextChunk(
                    id=chunk_id,
                    content=chunk_content,
                    source_url=source_url,
                    source_title=source_title,
                    chunk_index=chunk_index,
                    token_count=self.count_tokens(chunk_content),
                    char_count=len(chunk_content),
                    metadata={
                        "chunk_id": chunk_id,
                        "source_url": source_url,
                        "source_title": source_title,
                        "chunk_index": chunk_index,
                        "start_char": start,
                        "end_char": end
                    }
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start position (with overlap)
            start = end - chunk_overlap
            if start >= end:  # Prevent infinite loop
                start = end

        # Update metadata with total chunk count
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        logger.info(f"Created {len(chunks)} chunks from text of length {len(cleaned_text)}")

        return chunks

    def create_chunks_from_elements(
        self,
        text_elements: List,  # List of TextElement objects from scraper
        source_url: str,
        source_title: str
    ) -> List[TextChunk]:
        """Create chunks from a list of text elements.

        Args:
            text_elements: List of TextElement objects from scraper
            source_url: URL of the source document
            source_title: Title of the source document

        Returns:
            List of TextChunk objects
        """
        all_chunks = []

        for element in text_elements:
            element_chunks = self.create_chunks(
                element.content,
                source_url,
                source_title
            )

            # Add element-specific metadata
            for chunk in element_chunks:
                chunk.metadata.update({
                    "source_tag": element.tag,
                    "element_word_count": element.word_count,
                    "element_char_count": element.char_count
                })

            all_chunks.extend(element_chunks)

        # Re-index chunks globally
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(all_chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(text_elements)} text elements")

        return all_chunks