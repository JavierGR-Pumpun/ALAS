"""
ALAS — Auth DB
NeonDB (PostgreSQL) connection and schema initialization.
"""

import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

from app.logger import get_logger

logger = get_logger("auth.db")

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not _DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set in .env")
    return psycopg2.connect(_DATABASE_URL)


def init_db():
    """Create users and sessions tables if they don't exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id            SERIAL PRIMARY KEY,
        full_name     VARCHAR(100) NOT NULL,
        email         VARCHAR(100) UNIQUE NOT NULL,
        phone         VARCHAR(20),
        password_hash VARCHAR(255) NOT NULL,
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token      VARCHAR(64) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL
    );
    """
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        conn.close()
        logger.info("DB initialized (tables OK)")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        raise
