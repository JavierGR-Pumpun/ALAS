"""
ALAS — Auth Service
register, login, verify_session, logout against NeonDB.
"""

from __future__ import annotations
import re
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional

import bcrypt

from app.auth.db import get_connection
from app.logger import get_logger

logger = get_logger("auth.service")

_SESSION_DAYS = 30


@dataclass
class User:
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    created_at: datetime.datetime


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register(full_name: str, email: str, phone: str, password: str) -> User | str:
    """
    Create a new user. Returns User on success, error string on failure.
    """
    if not _valid_email(email):
        return "auth.error_invalid_email"

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (full_name, email, phone, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, full_name, email, phone, created_at
                    """,
                    (full_name.strip(), email.strip().lower(), phone.strip() or None, pw_hash),
                )
                row = cur.fetchone()
        conn.close()
        logger.info(f"User registered: {email}")
        return User(*row)
    except Exception as e:
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            return "auth.error_email_taken"
        logger.error(f"Register error: {e}")
        return "auth.error_processing_failed"


def login(email: str, password: str, remember_me: bool = False) -> tuple[User, str | None] | str:
    """
    Verify credentials. Returns (User, token_or_None) on success,
    error string on failure.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, full_name, email, phone, password_hash, created_at FROM users WHERE email = %s",
                (email.strip().lower(),),
            )
            row = cur.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"Login DB error: {e}")
        return "auth.error_processing_failed"

    if row is None:
        return "auth.error_invalid_credentials"

    user_id, full_name, db_email, phone, pw_hash, created_at = row
    if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        return "auth.error_invalid_credentials"

    user = User(user_id, full_name, db_email, phone, created_at)
    token = None

    if remember_me:
        token = _create_session(user_id)

    logger.info(f"User logged in: {email}")
    return user, token


def verify_session(token: str) -> Optional[User]:
    """Return User if token exists and hasn't expired, else None."""
    if not token:
        return None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.full_name, u.email, u.phone, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = %s AND s.expires_at > NOW()
                """,
                (token,),
            )
            row = cur.fetchone()
        conn.close()
        if row:
            return User(*row)
    except Exception as e:
        logger.warning(f"Session verify error: {e}")
    return None


def logout(token: str):
    """Delete the session row from DB."""
    if not token:
        return
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.close()
        logger.info("Session deleted")
    except Exception as e:
        logger.warning(f"Logout error: {e}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_session(user_id: int) -> str:
    token = uuid.uuid4().hex
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=_SESSION_DAYS)
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user_id, token, expires),
            )
    conn.close()
    return token


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))
