"""
ETL: School name canonicalization + alias mapping + review queue insert

Goal: "do both"
- Normalize now: produce a canonical school name used for matching Accounts
- Store alias mappings for scalability: persist raw variants -> canonical Account
- Queue uncertain names for human review in pd.etl_school_name_review_queue

Dependencies: rapidfuzz for fuzzy matching, psycopg v3, python-dotenv
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from rapidfuzz import fuzz, process

from .db import connect


@dataclass
class CanonicalizationResult:
    raw: str
    normalized: str
    account_id: Optional[int]
    matched_via: str  # "exact" | "fuzzy" | "none"
    score: Optional[float]  # similarity score if fuzzy


def _basic_normalize(name: str) -> str:
    """Lowercase, strip, remove common noise to help matching."""
    n = name.strip().lower()
    # Remove common suffix/prefix noise; keep beginner-friendly and simple.
    for token in ["university", "college", "inc.", "corp.", "llc", "univ."]:
        n = n.replace(token, "").strip()
    # Collapse extra spaces
    n = " ".join(n.split())
    return n


def fetch_account_candidates() -> list[tuple[int, str]]:
    """
    Load candidate Accounts (id, canonical_name) from pd.accounts.
    The table definition is assumed to include an id and name-like column.
    Adjust column names as needed to your schema.
    """
    sql = """
        select id, name
        from pd.accounts
        where type in ('academic', 'school') -- example filter; adjust if needed
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [(row[0], row[1]) for row in cur.fetchall()]


def match_school_to_account(raw_name: str, threshold: int = 87) -> CanonicalizationResult:
    """Match a raw school name to an existing Account via exact or fuzzy logic."""
    normalized = _basic_normalize(raw_name)
    candidates = fetch_account_candidates()  # [(id, name)]
    # Try exact match on normalized against candidate normalized names
    for account_id, candidate_name in candidates:
        if _basic_normalize(candidate_name) == normalized:
            return CanonicalizationResult(
                raw=raw_name,
                normalized=candidate_name,
                account_id=account_id,
                matched_via="exact",
                score=100.0,
            )

    # Fuzzy match using rapidfuzz
    choices = {account_id: candidate_name for account_id, candidate_name in candidates}
    # use token_set_ratio to ignore word order and duplicates
    best = None
    best_score = -1.0
    for account_id, candidate_name in choices.items():
        score = fuzz.token_set_ratio(normalized, _basic_normalize(candidate_name))
        if score > best_score:
            best = (account_id, candidate_name)
            best_score = score

    if best and best_score >= threshold:
        account_id, candidate_name = best
        return CanonicalizationResult(
            raw=raw_name,
            normalized=candidate_name,
            account_id=account_id,
            matched_via="fuzzy",
            score=best_score,
        )

    return CanonicalizationResult(
        raw=raw_name,
        normalized=normalized,
        account_id=None,
        matched_via="none",
        score=None,
    )


def upsert_alias_mapping(raw_name: str, account_id: int, source: str = "etl") -> None:
    """
    Persist alias mapping into pd.account_aliases.
    Assumes columns: id (serial), account_id (int), alias (text), source (text).
    """
    sql = """
        insert into pd.account_aliases (account_id, alias, source)
        values (%s, %s, %s)
        on conflict (account_id, alias) do update set source = excluded.source
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (account_id, raw_name, source))
        conn.commit()


def queue_for_review(raw_name: str, context: Optional[str] = None) -> None:
    """Insert uncertain names into pd.etl_school_name_review_queue for human review."""
    sql = """
        insert into pd.etl_school_name_review_queue (raw_name, context)
        values (%s, %s)
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (raw_name, context))
        conn.commit()


def canonicalize_school_name(raw_name: str, context: Optional[str] = None) -> CanonicalizationResult:
    """
    Public ETL entrypoint:
    - Normalize and match against accounts
    - If matched, upsert alias mapping
    - If not matched, queue for human review
    Returns a CanonicalizationResult for downstream usage.
    """
    result = match_school_to_account(raw_name)
    if result.account_id is not None:
        upsert_alias_mapping(raw_name, result.account_id, source="etl")
    else:
        queue_for_review(raw_name, context=context)
    return result


def process_batch(raw_names: Iterable[str], context: Optional[str] = None) -> list[CanonicalizationResult]:
    """Process a batch of raw school names and return results for logging/analysis."""
    results: list[CanonicalizationResult] = []
    for name in raw_names:
        results.append(canonicalize_school_name(name, context=context))
    return results