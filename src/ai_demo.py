"""
AI Demo (skeleton): example tool calls
- vector_search: uses pd.entity_embeddings (pgvector) to find similar entities
- safe_sql_query: uses safe_sql to run dynamic read-only queries on pd.v_* views
"""
from __future__ import annotations

from typing import Sequence

from .db import connect
from .safe_sql import run_safe_sql


def vector_search(query_vector: Sequence[float], top_k: int = 5):
    """Search pd.entity_embeddings using pgvector similarity. Adjust to your schema."""
    sql = """
        select entity_id, similarity
        from (
            select entity_id,
                   1 - (embedding <-> %s) as similarity  -- cosine distance example; adjust operator
            from pd.entity_embeddings
        ) s
        order by similarity desc
        limit %s
    """
    with connect() as conn, conn.cursor() as cur:
        # NOTE: pgvector uses specific parameter casting; adapt based on your extension setup
        cur.execute(sql, (list(query_vector), top_k))
        return cur.fetchall()


def safe_sql_query(sql: str):
    """Run a dynamic query safely via safe_sql module."""
    return run_safe_sql(sql)


if __name__ == "__main__":
    # Demo placeholders; replace with real vectors and queries
    print("Vector search demo (placeholder):", vector_search([0.1, 0.2, 0.3]))
    print("Safe SQL demo:")
    rows = safe_sql_query("select * from pd.v_accounts")
    for r in rows:
        print(r)