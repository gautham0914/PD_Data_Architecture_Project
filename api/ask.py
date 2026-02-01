from http.server import BaseHTTPRequestHandler
import os
import json
from typing import Dict, Any, List

from ._db import get_conn
from ._guardrails import enforce_readonly
from ._llm import generate_sql_with_llm

API_TOKEN = os.getenv("API_TOKEN")


def _parse_body(r: BaseHTTPRequestHandler) -> Dict[str, Any]:
    try:
        length = int(r.headers.get("Content-Length", "0"))
    except Exception:
        length = 0
    raw = r.rfile.read(length) if length > 0 else b""
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        return {}


def _get_schema_for_llm() -> Dict[str, Any]:
    # For grounding: include views and columns only (small)
    schema: Dict[str, Any] = {"views": [], "columns": {}}
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            select table_name
            from information_schema.views
            where table_schema = 'pd' and table_name like 'v_%'
            order by table_name
            """
        )
        views = [r[0] for r in cur.fetchall()]
        schema["views"] = [f"pd.{v}" for v in views]
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
            schema["columns"][f"pd.{v}"] = [r[0] for r in cur.fetchall()]
    return schema


def _audit(question: str, generated_sql: str, final_sql: str, status: str, row_count: int) -> None:
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into pd.query_audit_log (executed_at, user_id, query_text, outcome)
                values (now(), 'web_demo', %s, %s)
                """,
                (final_sql, f"{status} rows={row_count} question={question[:200]}")
            )
    except Exception:
        # Do not fail if audit table shape differs
        pass


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Token check
        if API_TOKEN:
            token = self.headers.get("x-api-token")
            if not token or token != API_TOKEN:
                out = json.dumps({"error": "unauthorized"}).encode("utf-8")
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
                return

        data = _parse_body(self)
        question = (data.get("question") or "").strip()
        if not question:
            out = json.dumps({"error": "missing_question"}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return

        # Fetch schema for grounding
        schema = _get_schema_for_llm()
        gen = generate_sql_with_llm(question, schema)
        if not gen.get("ok"):
            out = json.dumps({"error": gen.get("error", "llm_error")}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return

        generated_sql = gen.get("sql", "").strip()
        try:
            final_sql = enforce_readonly(generated_sql, default_limit=200)
        except Exception as e:
            _audit(question, generated_sql, generated_sql, "blocked", 0)
            out = json.dumps({
                "question": question,
                "generated_sql": generated_sql,
                "error": f"guardrail_blocked: {e}",
            }).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return

        # Execute safe SQL
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(final_sql)
                rows = cur.fetchall()
                cols: List[str] = [d.name for d in cur.description]
        except Exception as e:
            _audit(question, generated_sql, final_sql, "error", 0)
            out = json.dumps({
                "question": question,
                "generated_sql": generated_sql,
                "final_sql": final_sql,
                "error": str(e),
            }).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return

        _audit(question, generated_sql, final_sql, "ok", len(rows))
        payload = {
            "question": question,
            "generated_sql": generated_sql,
            "final_sql": final_sql,
            "columns": cols,
            "rows": rows,
            "meta": {"row_count": len(rows), "guardrails_applied": True},
        }
        out = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)
