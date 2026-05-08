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
    return psycopg2.connect(_DATABASE_URL, connect_timeout=5)

