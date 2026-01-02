"""Web scraping module for extracting text content from URLs."""

from .scraper import WebScraper, ScrapedContent
from .transcriber import process_video

__all__ = ["WebScraper", "ScrapedContent", "process_video"]