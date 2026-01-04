"""SQLite storage for content analysis results."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Use the same database as other storage
DATABASE_PATH = Path("./data/scrape_results.db")


@dataclass
class ContentAnalysis:
    """Represents a content analysis result."""
    id: str
    url: str
    url_hash: str
    source_type: Optional[str] = None  # "youtube" or "webpage"
    title: Optional[str] = None

    # Source assessment
    source_credibility: Optional[str] = None  # high/medium/low/unknown
    source_credibility_reasoning: Optional[str] = None
    source_potential_biases: Optional[List[str]] = None

    # Summary data
    executive_summary: Optional[str] = None
    key_points: Optional[List[Dict[str, str]]] = None  # [{point, location}]
    main_argument: Optional[str] = None
    conclusions: Optional[List[str]] = None

    # Status
    status: str = "pending"  # pending, in_progress, completed, failed
    error_message: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "url_hash": self.url_hash,
            "source_type": self.source_type,
            "title": self.title,
            "source_credibility": self.source_credibility,
            "source_credibility_reasoning": self.source_credibility_reasoning,
            "source_potential_biases": self.source_potential_biases or [],
            "executive_summary": self.executive_summary,
            "key_points": self.key_points or [],
            "main_argument": self.main_argument,
            "conclusions": self.conclusions or [],
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def hash_url(url: str) -> str:
    """Create SHA256 hash of URL for efficient lookups."""
    return hashlib.sha256(url.encode()).hexdigest()


class AnalysisStore:
    """SQLite storage for content analysis results."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_analyses (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    url_hash TEXT NOT NULL UNIQUE,
                    source_type TEXT,
                    title TEXT,
                    source_credibility TEXT,
                    source_credibility_reasoning TEXT,
                    source_potential_biases JSON,
                    executive_summary TEXT,
                    key_points JSON,
                    main_argument TEXT,
                    conclusions JSON,
                    status TEXT NOT NULL DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_analyses_url_hash
                ON content_analyses(url_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_analyses_status
                ON content_analyses(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_analyses_created_at
                ON content_analyses(created_at DESC)
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

    def create_or_update_analysis(
        self,
        url: str,
        source_type: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ContentAnalysis:
        """Create a new analysis record or update existing one for URL.

        If an analysis for this URL already exists, it will be reset to pending status.
        """
        url_hash_value = hash_url(url)
        now = datetime.now()

        with self._get_connection() as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT id FROM content_analyses WHERE url_hash = ?",
                (url_hash_value,)
            ).fetchone()

            if existing:
                # Update existing - reset to pending
                analysis_id = existing["id"]
                conn.execute(
                    """
                    UPDATE content_analyses
                    SET status = 'pending',
                        source_type = ?,
                        title = ?,
                        updated_at = ?,
                        error_message = NULL,
                        completed_at = NULL
                    WHERE id = ?
                    """,
                    (source_type, title, now.isoformat(), analysis_id)
                )
                logger.info(f"Reset analysis {analysis_id} for URL: {url[:50]}...")
            else:
                # Create new
                analysis_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO content_analyses
                    (id, url, url_hash, source_type, title, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (analysis_id, url, url_hash_value, source_type, title, now.isoformat())
                )
                logger.info(f"Created analysis {analysis_id} for URL: {url[:50]}...")

            conn.commit()

        return ContentAnalysis(
            id=analysis_id,
            url=url,
            url_hash=url_hash_value,
            source_type=source_type,
            title=title,
            status="pending",
            created_at=now
        )

    def save_analysis_results(
        self,
        analysis_id: str,
        summary: Dict[str, Any],
        source_assessment: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save the analysis results after summary step completes.

        Args:
            analysis_id: The analysis record ID
            summary: Dict with summary, main_argument, key_claims
            source_assessment: Optional dict with credibility, reasoning, potential_biases
        """
        now = datetime.now()

        # Extract fields from source_assessment (optional)
        credibility = None
        reasoning = None
        biases: list = []
        if source_assessment:
            credibility = source_assessment.get("credibility")
            reasoning = source_assessment.get("reasoning")
            biases = source_assessment.get("potential_biases", [])

        # Extract fields from summary (now includes key_claims instead of key_points/conclusions)
        executive_summary = summary.get("summary")
        key_claims = summary.get("key_claims", [])
        main_argument = summary.get("main_argument")

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE content_analyses
                SET source_credibility = ?,
                    source_credibility_reasoning = ?,
                    source_potential_biases = ?,
                    executive_summary = ?,
                    key_points = ?,
                    main_argument = ?,
                    status = 'completed',
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    credibility,
                    reasoning,
                    json.dumps(biases),
                    executive_summary,
                    json.dumps(key_claims),  # Store key_claims in key_points column
                    main_argument,
                    now.isoformat(),
                    now.isoformat(),
                    analysis_id
                )
            )
            conn.commit()
            success = cursor.rowcount > 0

        if success:
            logger.info(f"Saved analysis results for {analysis_id}")
        return success

    def update_status(
        self,
        analysis_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update the status of an analysis."""
        now = datetime.now()

        with self._get_connection() as conn:
            if status == "failed" and error_message:
                cursor = conn.execute(
                    """
                    UPDATE content_analyses
                    SET status = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, error_message, now.isoformat(), analysis_id)
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE content_analyses
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, now.isoformat(), analysis_id)
                )
            conn.commit()
            return cursor.rowcount > 0

    def get_analysis(self, analysis_id: str) -> Optional[ContentAnalysis]:
        """Get an analysis by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM content_analyses WHERE id = ?",
                (analysis_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_analysis(row)

    def get_analysis_by_url(self, url: str) -> Optional[ContentAnalysis]:
        """Get an analysis by URL."""
        url_hash_value = hash_url(url)

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM content_analyses WHERE url_hash = ?",
                (url_hash_value,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_analysis(row)

    def list_analyses(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List analyses with optional filtering.

        Returns:
            Tuple of (list of analysis dicts, total count)
        """
        with self._get_connection() as conn:
            # Get total count
            if status:
                count_row = conn.execute(
                    "SELECT COUNT(*) as total FROM content_analyses WHERE status = ?",
                    (status,)
                ).fetchone()
            else:
                count_row = conn.execute(
                    "SELECT COUNT(*) as total FROM content_analyses"
                ).fetchone()
            total = count_row["total"]

            # Get paginated results
            if status:
                rows = conn.execute(
                    """
                    SELECT id, url, source_type, title, executive_summary,
                           status, created_at, completed_at
                    FROM content_analyses
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, url, source_type, title, executive_summary,
                           status, created_at, completed_at
                    FROM content_analyses
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                ).fetchall()

        analyses = [
            {
                "id": row["id"],
                "url": row["url"],
                "source_type": row["source_type"],
                "title": row["title"],
                "executive_summary": row["executive_summary"],
                "status": row["status"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
            }
            for row in rows
        ]

        return analyses, total

    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete an analysis by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM content_analyses WHERE id = ?",
                (analysis_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted analysis {analysis_id}")
        return deleted

    def _row_to_analysis(self, row: sqlite3.Row) -> ContentAnalysis:
        """Convert a database row to a ContentAnalysis object."""
        # Parse JSON fields
        biases = None
        if row["source_potential_biases"]:
            biases = json.loads(row["source_potential_biases"])

        key_points = None
        if row["key_points"]:
            key_points = json.loads(row["key_points"])

        conclusions = None
        if row["conclusions"]:
            conclusions = json.loads(row["conclusions"])

        # Parse timestamps
        created_at = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = datetime.now()

        updated_at = None
        if row["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except ValueError:
                pass

        completed_at = None
        if row["completed_at"]:
            try:
                completed_at = datetime.fromisoformat(row["completed_at"])
            except ValueError:
                pass

        return ContentAnalysis(
            id=row["id"],
            url=row["url"],
            url_hash=row["url_hash"],
            source_type=row["source_type"],
            title=row["title"],
            source_credibility=row["source_credibility"],
            source_credibility_reasoning=row["source_credibility_reasoning"],
            source_potential_biases=biases,
            executive_summary=row["executive_summary"],
            key_points=key_points,
            main_argument=row["main_argument"],
            conclusions=conclusions,
            status=row["status"],
            error_message=row["error_message"],
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
        )
