"""SQLite storage for claim verification results."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Use the same database as scrape results
DATABASE_PATH = Path("./data/scrape_results.db")


@dataclass
class Evidence:
    """Represents a piece of evidence for or against a claim."""
    source_url: str
    source_title: str
    snippet: str
    credibility_score: Optional[float] = None
    credibility_reasoning: Optional[str] = None


@dataclass
class ClaimVerification:
    """Represents a claim verification result."""
    id: str
    claim_text: str
    source_url: str
    status: str  # pending, in_progress, completed, failed
    claim_id: Optional[str] = None
    evidence_for: Optional[List[Evidence]] = None
    evidence_against: Optional[List[Evidence]] = None
    conclusion: Optional[str] = None
    conclusion_type: Optional[str] = None  # supported, refuted, inconclusive
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "claim_text": self.claim_text,
            "source_url": self.source_url,
            "status": self.status,
            "claim_id": self.claim_id,
            "conclusion": self.conclusion,
            "conclusion_type": self.conclusion_type,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        if self.evidence_for:
            result["evidence_for"] = [asdict(e) for e in self.evidence_for]
        else:
            result["evidence_for"] = []

        if self.evidence_against:
            result["evidence_against"] = [asdict(e) for e in self.evidence_against]
        else:
            result["evidence_against"] = []

        return result


class VerificationStore:
    """SQLite storage for claim verification results."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claim_verifications (
                    id TEXT PRIMARY KEY,
                    claim_text TEXT NOT NULL,
                    claim_id TEXT,
                    source_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    evidence_for JSON,
                    evidence_against JSON,
                    conclusion TEXT,
                    conclusion_type TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
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

    def create_verification(
        self,
        claim_text: str,
        source_url: str,
        claim_id: Optional[str] = None
    ) -> ClaimVerification:
        """Create a new pending verification and return it."""
        verification_id = str(uuid.uuid4())
        created_at = datetime.now()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO claim_verifications
                (id, claim_text, claim_id, source_url, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (verification_id, claim_text, claim_id, source_url, created_at.isoformat())
            )
            conn.commit()

        logger.info(f"Created verification {verification_id} for claim: {claim_text[:50]}...")

        return ClaimVerification(
            id=verification_id,
            claim_text=claim_text,
            source_url=source_url,
            status="pending",
            claim_id=claim_id,
            created_at=created_at
        )

    def get_verification(self, verification_id: str) -> Optional[ClaimVerification]:
        """Get a verification by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM claim_verifications WHERE id = ?",
                (verification_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_verification(row)

    def update_status(
        self,
        verification_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update the status of a verification."""
        with self._get_connection() as conn:
            if status == "failed" and error_message:
                cursor = conn.execute(
                    """
                    UPDATE claim_verifications
                    SET status = ?, error_message = ?
                    WHERE id = ?
                    """,
                    (status, error_message, verification_id)
                )
            else:
                cursor = conn.execute(
                    "UPDATE claim_verifications SET status = ? WHERE id = ?",
                    (status, verification_id)
                )
            conn.commit()
            return cursor.rowcount > 0

    def save_results(
        self,
        verification_id: str,
        evidence_for: List[Evidence],
        evidence_against: List[Evidence],
        conclusion: str,
        conclusion_type: str
    ) -> bool:
        """Save the verification results."""
        completed_at = datetime.now()

        evidence_for_json = json.dumps([asdict(e) for e in evidence_for])
        evidence_against_json = json.dumps([asdict(e) for e in evidence_against])

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE claim_verifications
                SET evidence_for = ?,
                    evidence_against = ?,
                    conclusion = ?,
                    conclusion_type = ?,
                    status = 'completed',
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    evidence_for_json,
                    evidence_against_json,
                    conclusion,
                    conclusion_type,
                    completed_at.isoformat(),
                    verification_id
                )
            )
            conn.commit()
            success = cursor.rowcount > 0

        if success:
            logger.info(f"Saved results for verification {verification_id}")
        return success

    def get_verification_by_claim(
        self,
        claim_id: Optional[str] = None,
        claim_text: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> Optional[ClaimVerification]:
        """Get the most recent verification for a claim.

        Args:
            claim_id: The claim ID to search for
            claim_text: The claim text to search for (exact match)
            source_url: The source URL (required if using claim_text)

        Returns:
            The most recent ClaimVerification for the claim, or None
        """
        with self._get_connection() as conn:
            if claim_id:
                row = conn.execute(
                    """
                    SELECT * FROM claim_verifications
                    WHERE claim_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (claim_id,)
                ).fetchone()
            elif claim_text and source_url:
                row = conn.execute(
                    """
                    SELECT * FROM claim_verifications
                    WHERE claim_text = ? AND source_url = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (claim_text, source_url)
                ).fetchone()
            else:
                return None

        if not row:
            return None

        return self._row_to_verification(row)

    def list_verifications(
        self,
        source_url: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List verifications, optionally filtered by source URL."""
        with self._get_connection() as conn:
            if source_url:
                rows = conn.execute(
                    """
                    SELECT id, claim_text, source_url, status, conclusion_type,
                           created_at, completed_at
                    FROM claim_verifications
                    WHERE source_url = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (source_url, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, claim_text, source_url, status, conclusion_type,
                           created_at, completed_at
                    FROM claim_verifications
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                ).fetchall()

        return [
            {
                "id": row["id"],
                "claim_text": row["claim_text"],
                "source_url": row["source_url"],
                "status": row["status"],
                "conclusion_type": row["conclusion_type"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
            }
            for row in rows
        ]

    def delete_verification(self, verification_id: str) -> bool:
        """Delete a verification by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM claim_verifications WHERE id = ?",
                (verification_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted verification {verification_id}")
        return deleted

    def _row_to_verification(self, row: sqlite3.Row) -> ClaimVerification:
        """Convert a database row to a ClaimVerification object."""
        evidence_for = None
        evidence_against = None

        if row["evidence_for"]:
            evidence_for_data = json.loads(row["evidence_for"])
            evidence_for = [Evidence(**e) for e in evidence_for_data]

        if row["evidence_against"]:
            evidence_against_data = json.loads(row["evidence_against"])
            evidence_against = [Evidence(**e) for e in evidence_against_data]

        created_at = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = datetime.now()

        completed_at = None
        if row["completed_at"]:
            try:
                completed_at = datetime.fromisoformat(row["completed_at"])
            except ValueError:
                pass

        return ClaimVerification(
            id=row["id"],
            claim_text=row["claim_text"],
            claim_id=row["claim_id"],
            source_url=row["source_url"],
            status=row["status"],
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            conclusion=row["conclusion"],
            conclusion_type=row["conclusion_type"],
            error_message=row["error_message"],
            created_at=created_at,
            completed_at=completed_at
        )
