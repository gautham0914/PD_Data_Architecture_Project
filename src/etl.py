"""
ETL: Name canonicalization + alias mapping + review queue insert

Matches raw names (school/company) to pd.accounts using:
1) exact match on name_canonical
2) exact match on account_aliases.alias_name
3) fuzzy match (rapidfuzz) against accounts.name_canonical
If matched: insert alias mapping into pd.account_aliases (raw -> account_id)
If not matched: insert into pd.etl_school_name_review_queue for human review
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

from .db import connect


@dataclass
class CanonicalizationResult:
    raw: str
    normalized: str
    account_id: Optional[uuid.UUID]
    matched_via: str  # "canonical_exact" | "alias_exact" | "fuzzy" | "none"
    score: Optional[float]


def _normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s


def fetch_account_candidates(cur, account_type_hint: Optional[str] = None) -> list[tuple[uuid.UUID, str]]:
    """
    Returns [(account_id, name_canonical)] filtered by account_type if provided.
    Uses the SAME cursor/connection as seed.py (no new connection).
    """
    if account_type_hint is None:
        cur.execute("SELECT account_id, name_canonical FROM pd.accounts")
        return cur.fetchall()

    cur.execute(
        "SELECT account_id, name_canonical FROM pd.accounts WHERE account_type = %s",
        (account_type_hint,),
    )
    return cur.fetchall()



def match_raw_to_account(cur, raw_name: str, account_type_hint: Optional[str], threshold: int = 88) -> CanonicalizationResult:
    raw_norm = _normalize_text(raw_name)

    # 1) canonical exact
    if account_type_hint is None:
        cur.execute(
            """
            SELECT account_id, name_canonical
            FROM pd.accounts
            WHERE regexp_replace(lower(name_canonical), '[^a-z0-9 ]', '', 'g') = %s
            LIMIT 1
            """,
            (raw_norm,),
        )
    else:
        cur.execute(
            """
            SELECT account_id, name_canonical
            FROM pd.accounts
            WHERE account_type = %s
              AND regexp_replace(lower(name_canonical), '[^a-z0-9 ]', '', 'g') = %s
            LIMIT 1
            """,
            (account_type_hint, raw_norm),
        )

    row = cur.fetchone()
    if row:
        return CanonicalizationResult(raw=raw_name, normalized=row[1], account_id=row[0], matched_via="canonical_exact", score=100.0)

    # 2) alias exact
    if account_type_hint is None:
        cur.execute(
            """
            SELECT aa.account_id, a.name_canonical
            FROM pd.account_aliases aa
            JOIN pd.accounts a ON a.account_id = aa.account_id
            WHERE regexp_replace(lower(aa.alias_name), '[^a-z0-9 ]', '', 'g') = %s
            LIMIT 1
            """,
            (raw_norm,),
        )
    else:
        cur.execute(
            """
            SELECT aa.account_id, a.name_canonical
            FROM pd.account_aliases aa
            JOIN pd.accounts a ON a.account_id = aa.account_id
            WHERE a.account_type = %s
              AND regexp_replace(lower(aa.alias_name), '[^a-z0-9 ]', '', 'g') = %s
            LIMIT 1
            """,
            (account_type_hint, raw_norm),
        )

    row = cur.fetchone()
    if row:
        return CanonicalizationResult(raw=raw_name, normalized=row[1], account_id=row[0], matched_via="alias_exact", score=100.0)

    # 3) fuzzy vs canonical candidates
    candidates = fetch_account_candidates(cur, account_type_hint)
    best_id: Optional[uuid.UUID] = None
    best_name: Optional[str] = None
    best_score: float = -1.0

    for aid, cname in candidates:
        score = fuzz.token_set_ratio(raw_norm, _normalize_text(cname))
        if score > best_score:
            best_score = score
            best_id = aid
            best_name = cname

    if best_id is not None and best_name is not None and best_score >= threshold:
        return CanonicalizationResult(raw=raw_name, normalized=best_name, account_id=best_id, matched_via="fuzzy", score=best_score)

    return CanonicalizationResult(raw=raw_name, normalized=raw_norm, account_id=None, matched_via="none", score=None)


def upsert_alias_mapping(cur, raw_name: str, account_id: uuid.UUID, source_system: str = "etl") -> None:
    """
    Insert raw variant into account_aliases pointing to the matched account_id.
    Your schema has UNIQUE(alias_name) so use ON CONFLICT(alias_name).
    """
    cur.execute(
        """
        INSERT INTO pd.account_aliases (alias_id, account_id, alias_name, source_system, created_at)
        VALUES (%s,%s,%s,%s,now())
        ON CONFLICT (alias_name)
        DO UPDATE SET account_id = EXCLUDED.account_id, source_system = EXCLUDED.source_system
        """,
        (uuid.uuid4(), account_id, raw_name, source_system),
    )


def queue_for_review(cur, raw_name: str, notes: str = "Unmatched raw input") -> None:
    cur.execute(
        """
        INSERT INTO pd.etl_school_name_review_queue
          (queue_id, raw_school_name, suggested_account_id, confidence_score, status, notes, created_at, decided_at)
        VALUES (%s,%s,NULL,NULL,'pending',%s,now(),NULL)
        """,
        (uuid.uuid4(), raw_name, notes),
    )


def canonicalize_raw_name(cur, raw_name: str, *, account_type_hint: Optional[str], source_system: str) -> CanonicalizationResult:
    """
    Main entry:
    - match
    - if matched: upsert alias mapping
    - else: queue for review
    """
    result = match_raw_to_account(cur, raw_name, account_type_hint=account_type_hint)
    if result.account_id is not None:
        upsert_alias_mapping(cur, raw_name, result.account_id, source_system=source_system)
    else:
        queue_for_review(cur, raw_name, notes=f"Unmatched raw input from {source_system}. hint={account_type_hint}")
    return result


def ensure_account_for_raw_company(cur, raw_company: str) -> uuid.UUID:
    """
    Seed-only helper: ensure a company account exists for an unmatched raw company.

    Behavior:
    - Try to match via canonicalization first (company hint). If matched, return that id.
    - If still unmatched: create a new pd.accounts row with:
        account_type = 'company'
        name_canonical = title-cased raw input
        industry_primary = 'Unknown'
        website/linkedin_url = NULL
    Returns the account_id (UUID).
    """
    res = canonicalize_raw_name(cur, raw_company, account_type_hint="company", source_system="seed_fallback")
    if res.account_id is not None:
        return res.account_id

    # Create placeholder company to preserve FK integrity
    account_id = uuid.uuid4()
    name_canonical = raw_company.strip().title()
    cur.execute(
        """
        INSERT INTO pd.accounts (account_id, account_type, name_canonical, website, linkedin_url, industry_primary, created_at)
        VALUES (%s,'company',%s,NULL,NULL,'Unknown',now())
        """,
        (account_id, name_canonical),
    )
    # Also store alias mapping so future occurrences map cleanly
    upsert_alias_mapping(cur, raw_company, account_id, source_system="seed_placeholder")
    return account_id
