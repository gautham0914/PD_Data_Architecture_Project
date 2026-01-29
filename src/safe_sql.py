"""
Safe SQL validator/executor for dynamic queries
- Enforces SELECT-only
- Restricts sources to pd.v_* views (read-only layer)
- Forces a LIMIT if missing
"""
from __future__ import annotations

import re
from typing import Optional

from .db import connect


DISALLOWED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "grant", "revoke",
    "truncate", "comment", "copy"
}


def validate_and_rewrite(sql: str, default_limit: int = 100) -> str:
    """
    Validate the SQL is safe and rewrite to enforce LIMIT.

    Rules:
    - Must start with SELECT (case-insensitive, whitespace allowed)
    - Must reference only pd.v_* objects in FROM/JOIN clauses
    - Must not contain DDL/DML keywords
    - If LIMIT missing, append LIMIT {default_limit}
    """
    s = sql.strip()
    # Must be SELECT-only
    if not re.match(r"^\s*select\b", s, re.IGNORECASE):
        raise ValueError("Only SELECT statements are permitted.")

    # Disallow dangerous keywords anywhere
    if re.search(r"\b(" + "|".join(DISALLOWED_KEYWORDS) + r")\b", s, re.IGNORECASE):
        raise ValueError("Statement contains disallowed keywords.")

    # Extract identifiers in FROM/JOIN and validate pd.v_*
    identifiers = re.findall(r"\b(?:from|join)\s+([a-zA-Z0-9_.\"]+)", s, re.IGNORECASE)
    for ident in identifiers:
        # strip optional quotes
        ident_clean = ident.replace('"', '')
        if not ident_clean.startswith("pd.v_"):
            raise ValueError("Queries must use read-only views named pd.v_* only.")

    # If LIMIT missing, append one
    if not re.search(r"\blimit\b", s, re.IGNORECASE):
        s = s.rstrip("; ") + f"\nlimit {default_limit};"
    return s


def run_safe_sql(sql: str) -> list[tuple]:
    """
    Validate and execute the query safely. Optionally log audit events.
    Returns rows as a list of tuples. Beginner-friendly: no ORM.
    """
    safe_sql = validate_and_rewrite(sql)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(safe_sql)
        rows = cur.fetchall()
        # Optional: log query in pd.query_audit_log; adjust columns to your schema.
        try:
            cur.execute(
                "insert into pd.query_audit_log (query_text, is_safe) values (%s, %s)",
                (safe_sql, True),
            )
            conn.commit()
        except Exception:
            # If audit table shape differs, ignore logging rather than failing user queries.
            conn.rollback()
        return rows