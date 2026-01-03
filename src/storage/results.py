"""SQLite storage for scraping results."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)

DATABASE_PATH = Path("./data/scrape_results.db")


@dataclass
class ScrapeResult:
    """Represents a saved scraping result."""
    id: int
    name: str
    url: str
    title: Optional[str]
    content: str
    char_count: int
    saved_at: datetime
    vector_collection: Optional[str]


class ResultsStore:
    """SQLite storage for scraping results."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    char_count INTEGER,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vector_collection TEXT
                )
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_result(
        self,
        name: str,
        url: str,
        title: Optional[str],
        content: str
    ) -> int:
        """Save a scraping result and return its ID."""
        char_count = len(content)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scrape_results (name, url, title, content, char_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, url, title, content, char_count)
            )
            conn.commit()
            result_id = cursor.lastrowid

        logger.info(f"Saved scrape result '{name}' with ID {result_id}")
        return result_id

    def list_results(self) -> List[Dict[str, Any]]:
        """Get all saved results (without full content for performance)."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, url, title, char_count, saved_at, vector_collection,
                       substr(content, 1, 150) as preview
                FROM scrape_results
                ORDER BY saved_at DESC
                """
            ).fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "url": row["url"],
                "title": row["title"],
                "char_count": row["char_count"],
                "saved_at": row["saved_at"],
                "vector_collection": row["vector_collection"],
                "preview": row["preview"] + "..." if row["preview"] and len(row["preview"]) >= 150 else row["preview"]
            }
            for row in rows
        ]

    def get_result(self, result_id: int) -> Optional[ScrapeResult]:
        """Get a single result by ID including full content."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scrape_results WHERE id = ?",
                (result_id,)
            ).fetchone()

        if not row:
            return None

        return ScrapeResult(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            title=row["title"],
            content=row["content"],
            char_count=row["char_count"],
            saved_at=datetime.fromisoformat(row["saved_at"]) if row["saved_at"] else datetime.now(),
            vector_collection=row["vector_collection"]
        )

    def delete_result(self, result_id: int) -> bool:
        """Delete a result by ID. Returns True if deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM scrape_results WHERE id = ?",
                (result_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted scrape result with ID {result_id}")
        return deleted

    def update_vector_collection(self, result_id: int, collection_name: str) -> bool:
        """Update the vector_collection field for a result."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE scrape_results SET vector_collection = ? WHERE id = ?",
                (collection_name, result_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_vector_collection(self, result_id: int) -> bool:
        """Clear the vector_collection field (set to NULL)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE scrape_results SET vector_collection = NULL WHERE id = ?",
                (result_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
