"""Main entry point for the web scraping and RAG application."""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from cli import create_app


def main():
    """Main entry point for the application."""
    app = create_app()
    app()


if __name__ == "__main__":
    main()