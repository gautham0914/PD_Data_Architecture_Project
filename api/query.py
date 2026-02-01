import os
import json
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, List
from ._db import get_conn
from ._guardrails import enforce_readonly

API_TOKEN = os.getenv("API_TOKEN")

# Map query_id to SQL (views only)
QUERIES: Dict[str, str] = {
    "q1_cbre_boston_completed": """
with completed_students as (
  select distinct c.contact_id, (c.first_name||' '||c.last_name) as full_name
  from pd.v_experiences e
  join pd.v_opportunities o on o.opportunity_id = e.opportunity_id
  left join pd.v_opportunity_sponsorships s on s.opportunity_id = o.opportunity_id
  join pd.v_contacts c on c.contact_id = e.contact_id
  where o.season = 'Spring' and o.year = 2026
    and o.name ilike '%CRE Virtual Internship%' and o.name ilike '%CBRE%' and o.name ilike '%Boston%'
    and s.sponsor_display_name ilike '%CBRE%'
    and c.contact_type = 'student' and e.status = 'completed'
)
select
  (select count(*) from completed_students) as completed_students,
  (select string_agg(full_name, ', ' order by full_name) from completed_students) as student_names;
""",
    "q2_hofstra_2024_applicants": """
select
  count(distinct a.contact_id) as hofstra_applicants_2024
from pd.v_applications a
join pd.v_contacts c on c.contact_id = a.contact_id
join pd.v_accounts sch on sch.account_id = c.primary_school_account_id
where sch.name_canonical = 'Hofstra University'
  and coalesce(a.submitted_at, a.created_at) >= date '2024-01-01'
  and coalesce(a.submitted_at, a.created_at) <  date '2025-01-01';
""",
    "q3_fall_2025_corporate_sponsors_count": """
select
  count(distinct s.sponsor_display_name) as corporate_partners_fall_2025
from pd.v_opportunities o
left join pd.v_opportunity_sponsorships s on s.opportunity_id = o.opportunity_id
where o.season = 'Fall' and o.year = 2025 and s.sponsor_display_name is not null;
""",
    "q4_spring_2026_re_dev_alumni": """
with spring_2026_alumni as (
  select distinct e.contact_id
  from pd.v_experiences e
  join pd.v_opportunities o on o.opportunity_id = e.opportunity_id
  join pd.v_contacts c on c.contact_id = e.contact_id
  where o.season = 'Spring' and o.year = 2026
    and e.status = 'completed' and c.contact_type = 'student'
), latest_jobs as (
  select we.contact_id, we.company_account_id,
         row_number() over (partition by we.contact_id order by we.created_at desc) as rn
  from pd.v_work_experiences we
)
select count(distinct lj.contact_id) as alumni_in_real_estate_development
from spring_2026_alumni a
join latest_jobs lj on lj.contact_id = a.contact_id and lj.rn = 1
join pd.v_accounts company on company.account_id = lj.company_account_id
where company.industry_primary = 'Real Estate Development';
""",
    "q5_reengage_hines_summary": """
select 'Hines' as recommended_partner, 'Stale engagement with strong outcomes' as rationale
from pd.v_partner_engagements
limit 1;
""",
}


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


def _get_query_param(request: Any, name: str) -> str:
    # Try common request shapes for query params
    try:
        args = getattr(request, "args", None)
        if isinstance(args, dict) and name in args:
            val = args.get(name)
            return val if isinstance(val, str) else str(val)
    except Exception:
        pass

    try:
        query = getattr(request, "query", None)
        if isinstance(query, dict) and name in query:
            val = query.get(name)
            return val if isinstance(val, str) else str(val)
    except Exception:
        pass

    try:
        params = getattr(request, "params", None)
        if isinstance(params, dict) and name in params:
            val = params.get(name)
            return val if isinstance(val, str) else str(val)
    except Exception:
        pass

    try:
        url = getattr(request, "url", None)
        if isinstance(url, str):
            qs = parse_qs(urlparse(url).query)
            if name in qs and qs[name]:
                return qs[name][0]
    except Exception:
        pass

    return ""


def handler(request: Any):
    # Token check
    if API_TOKEN:
        token = request.headers.get("x-api-token") if hasattr(request, "headers") else None
        if not token or token != API_TOKEN:
            return {"error": "unauthorized"}, 401

    data = _parse_json(request)
    qid = (data.get("query_id") or "").strip()
    if not qid:
        # Support GET or missing JSON by reading query string
        qid = (_get_query_param(request, "query_id") or _get_query_param(request, "qid") or "").strip()
    if qid not in QUERIES:
        return {"error": "unknown_query_id"}, 400

    sql = QUERIES[qid]
    try:
        safe_sql = enforce_readonly(sql)
    except Exception as e:
        return {"error": f"guardrail_error: {e}"}, 400

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(safe_sql)
        rows = cur.fetchall()
        cols: List[str] = [d.name for d in cur.description]
    return {"query_id": qid, "columns": cols, "rows": rows}
