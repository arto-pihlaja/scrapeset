#!/usr/bin/env python3
"""Entry point script for the web scraping and RAG application."""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from src.main import main

if __name__ == "__main__":
    main()