import os
import psycopg

_conn = None

def get_conn() -> psycopg.Connection:
    """Lazy-connect to Postgres using DATABASE_URL env.
    - Autocommit enabled for simple read-only queries.
    - Creates the connection on first call to avoid import-time failures.
    """
    global _conn
    if _conn is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL env var is not set.")
        _conn = psycopg.connect(dsn, autocommit=True)
    return _conn
