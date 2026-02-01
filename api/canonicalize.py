import os
import json
from typing import Any, Dict
from rapidfuzz import process, fuzz
from ._db import get_conn

API_TOKEN = os.getenv("API_TOKEN")


def _parse_json(request: Any) -> Dict[str, Any]:
    try:
        return request.json()
    except Exception:
        try:
            body = getattr(request, "body", b"")
            if isinstance(body, (bytes, bytearray)):
                return json.loads(body.decode("utf-8"))
            elif isinstance(body, str):
                return json.loads(body)
        except Exception:
            return {}
    return {}


def handler(request: Any):
    # Token check
    if API_TOKEN:
        token = request.headers.get("x-api-token") if hasattr(request, "headers") else None
        if not token or token != API_TOKEN:
            return {"error": "unauthorized"}, 401

    data = _parse_json(request)
    raw = (data.get("raw_name") or "").strip()
    if not raw:
        return {"error": "missing_raw_name"}, 400

    conn = get_conn()
    with conn.cursor() as cur:
        # 1) Exact alias match (case-insensitive) → join accounts to get canonical
        cur.execute(
            """
            select a.name_canonical
            from pd.account_aliases aa
            join pd.accounts a on a.account_id = aa.account_id
            where lower(aa.alias_name) = lower(%s)
              and a.account_type in ('academic_institution','school')
            limit 1
            """,
            (raw,)
        )
        row = cur.fetchone()
        if row:
            return {
                "raw_name": raw,
                "canonical_name": row[0],
                "confidence": 100,
                "action": "store_mapping (already known alias)",
            }

        # 2) Fuzzy against canonical school accounts
        cur.execute(
            """
            select name_canonical
            from pd.accounts
            where account_type in ('academic_institution','school')
            """
        )
        names = [r[0] for r in cur.fetchall()]
        if not names:
            return {
                "raw_name": raw,
                "canonical_name": None,
                "confidence": 0,
                "action": "review_queue",
            }
        match = process.extractOne(raw, names, scorer=fuzz.WRatio)
        canonical = match[0] if match else None
        score = int(match[1]) if match else 0
        action = "store_mapping" if score >= 85 else "review_queue"
        return {
            "raw_name": raw,
            "canonical_name": canonical,
            "confidence": score,
            "action": action,
        }
