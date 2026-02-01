from http.server import BaseHTTPRequestHandler
import json
from typing import Dict, Any, List

from ._db import get_conn


def _get_schema() -> Dict[str, Any]:
    """Return compact schema: views list, columns per view, sample rows (small)."""
    views: List[str] = []
    columns: Dict[str, List[str]] = {}
    samples: Dict[str, List[List[Any]]] = {}

    conn = get_conn()
    with conn.cursor() as cur:
        # List pd.v_* views
        cur.execute(
            """
            select table_name
            from information_schema.views
            where table_schema = 'pd'
              and table_name like 'v_%'
            order by table_name
            """
        )
        views = [r[0] for r in cur.fetchall()]

        # Columns per view
        for v in views:
            cur.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'pd' and table_name = %s
                order by ordinal_position
                """,
                (v,)
            )
            columns[v] = [r[0] for r in cur.fetchall()]

        # Small samples (up to 2 rows per view)
        for v in views:
            try:
                cur.execute(f"select * from pd.{v} limit 2")
                rows = cur.fetchall()
                samples[v] = rows
            except Exception:
                samples[v] = []

    return {"views": [f"pd.{v}" for v in views], "columns": columns, "samples": samples}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            payload = _get_schema()
            out = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            err = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
