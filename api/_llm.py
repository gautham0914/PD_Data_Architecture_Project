import os
from typing import Dict, Any, Optional

# OpenAI SDK (python). Ensure 'openai' is in requirements and env OPENAI_API_KEY set.
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # handled below

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def generate_sql_with_llm(question: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Call OpenAI to generate SQL for the given question.
    Returns dict with keys: {'ok': bool, 'sql': str, 'error': str}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return {"ok": False, "error": "OPENAI_API_KEY not set; AI Query Console disabled"}

    client = OpenAI(api_key=api_key)

    # Build compact schema prompt: list views + columns; keep small
    views_desc = []
    for v in schema.get("views", []):
        cols = ", ".join(schema.get("columns", {}).get(v, []))
        views_desc.append(f"- {v}({cols})")
    schema_text = "\n".join(views_desc)

    examples = [
        "-- Top 5 schools by applicants\nselect sch.name_canonical as school, count(*) as applicants\nfrom pd.v_applications a\njoin pd.v_contacts c on c.contact_id = a.contact_id\njoin pd.v_accounts sch on sch.account_id = c.primary_school_account_id\ngroup by sch.name_canonical\norder by applicants desc\nlimit 5;",
        "-- Count completed students for Spring 2026\nselect count(distinct c.contact_id) as completed_students\nfrom pd.v_experiences e\njoin pd.v_opportunities o on o.opportunity_id = e.opportunity_id\njoin pd.v_contacts c on c.contact_id = e.contact_id\nwhere o.season = 'Spring' and o.year = 2026 and e.status = 'completed' and c.contact_type = 'student'\nlimit 200;",
        "-- Sponsors in Fall 2025\nselect count(distinct s.sponsor_display_name) as corporate_partners_fall_2025\nfrom pd.v_opportunities o\nleft join pd.v_opportunity_sponsorships s on s.opportunity_id = o.opportunity_id\nwhere o.season = 'Fall' and o.year = 2025 and s.sponsor_display_name is not null\nlimit 200;",
        "-- Top companies by hires\nselect company.name_canonical as company, count(*) as hires\nfrom pd.v_work_experiences we\njoin pd.v_accounts company on company.account_id = we.company_account_id\ngroup by company.name_canonical\norder by hires desc\nlimit 10;",
    ]

    system = (
        "You are a helpful SQL assistant. Generate ONE safe SQL query using only pd.v_* views. "
        "Strict rules: SELECT or WITH only; no DDL/DML; block system schemas; prefer simple aggregates; always include a reasonable LIMIT; "
        "Output SQL only (no prose, no markdown)."
    )
    user = (
        f"Schema (views → columns):\n{schema_text}\n\n"
        f"Question: {question}\n\n"
        f"Examples:\n" + "\n\n".join(examples)
    )

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        sql = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "sql": sql}
    except Exception as e:
        return {"ok": False, "error": str(e)}
