"""
Database connection helper for Neon Postgres
- Uses DATABASE_URL from environment (.env via python-dotenv)
- Psycopg v3 (psycopg[binary])
- Beginner-readable, no hardcoded credentials
"""
from __future__ import annotations

import os
from typing import Iterable, Optional
from pathlib import Path

from dotenv import load_dotenv
import psycopg

from psycopg import Connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Load .env from project root so it works regardless of CWD
load_dotenv(PROJECT_ROOT / ".env")

def _load_env() -> None:
    """Load environment variables from .env once."""
    # Safe to call multiple times; load_dotenv caches.
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def get_database_url() -> str:
    """Return the DATABASE_URL from environment; raise if missing."""
    _load_env()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Create .env or export it in the shell."
        )
    return url


def connect() -> Connection:
    """
    Create a psycopg v3 connection to Neon using the DSN in DATABASE_URL.

    Example:
        >>> with connect() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("select 1")
        ...         print(cur.fetchone())
    """
    dsn = get_database_url()
    # psycopg connects with autocommit=False by default.
    conn: Connection = psycopg.connect(dsn)
    return conn


def execute(sql: str, params: Optional[Iterable] = None) -> None:
    """Convenience: run a single statement within a transaction."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()


def query_one(sql: str, params: Optional[Iterable] = None):
    """Run a query and return a single row (or None)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def query_all(sql: str, params: Optional[Iterable] = None):
    """Run a query and return all rows."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()