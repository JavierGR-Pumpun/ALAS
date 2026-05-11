"""
ALAS — Analysis Reports Service
CRUD for the analysis_reports table on NeonDB.
"""

from __future__ import annotations
import uuid
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from app.auth.db import get_connection
from app.logger import get_logger

logger = get_logger("auth.reports_service")


@dataclass
class AnalysisReport:
    id: int
    user_id: int
    title: str
    filename: str
    disk_path: str
    size_bytes: int
    share_token: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def is_shared(self) -> bool:
        return self.share_token is not None

    @property
    def size_human(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 ** 2:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / (1024 ** 2):.1f} MB"

    @property
    def date_str(self) -> str:
        if self.created_at:
            import datetime
            local_dt = self.created_at.astimezone(datetime.timezone.utc).astimezone()
            return local_dt.strftime("%d/%m/%Y %H:%M")
        return "—"


def save_report(user_id: int, title: str, disk_path: str) -> AnalysisReport | str:
    """Save a PDF report record to DB. Returns AnalysisReport on success, error key on failure."""
    p = Path(disk_path)
    if not p.exists():
        return "reports.error_file_not_found"

    filename = p.name
    size_bytes = p.stat().st_size

    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_reports
                        (user_id, title, filename, disk_path, size_bytes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id, user_id, title, filename, disk_path, size_bytes,
                              share_token, created_at, updated_at
                    """,
                    (user_id, title.strip(), filename, str(p.resolve()), size_bytes),
                )
                row = cur.fetchone()
        conn.close()
        logger.info(f"Report saved: {filename} for user {user_id}")
        return AnalysisReport(*row)
    except Exception as e:
        logger.error(f"save_report error: {e}")
        return "reports.error_save_failed"


def get_user_reports(user_id: int) -> List[AnalysisReport]:
    """Return all reports for a user, newest first."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, title, filename, disk_path, size_bytes,
                           share_token, created_at, updated_at
                    FROM analysis_reports
                    WHERE user_id = %s
                    ORDER BY COALESCE(created_at, updated_at, '1970-01-01'::timestamptz) DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        conn.close()
        return [AnalysisReport(*row) for row in rows]
    except Exception as e:
        logger.error(f"get_user_reports error (user_id={user_id}): {e}")
        return []


def delete_report(report_id: int, user_id: int) -> bool:
    """Delete a report record (does NOT remove the file). Returns True on success."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM analysis_reports WHERE id = %s AND user_id = %s RETURNING id",
                    (report_id, user_id),
                )
                deleted = cur.fetchone()
        conn.close()
        return deleted is not None
    except Exception as e:
        logger.error(f"delete_report error: {e}")
        return False


def toggle_share(report_id: int, user_id: int) -> Optional[str]:
    """
    Toggle the share token on/off.
    Returns the new token if now shared, None if now unshared.
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT share_token FROM analysis_reports WHERE id = %s AND user_id = %s",
                    (report_id, user_id),
                )
                row = cur.fetchone()
                if row is None:
                    conn.close()
                    return None
                current_token = row[0]
                new_token = None if current_token is not None else uuid.uuid4().hex
                cur.execute(
                    """UPDATE analysis_reports
                       SET share_token = %s, updated_at = NOW()
                       WHERE id = %s AND user_id = %s""",
                    (new_token, report_id, user_id),
                )
        conn.close()
        return new_token
    except Exception as e:
        logger.error(f"toggle_share error: {e}")
        return None
