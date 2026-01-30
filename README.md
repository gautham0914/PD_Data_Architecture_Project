# PD_Data_Architecture_Project: Data Architecture + Python ETL + AI-ready

## Architecture
- Postgres (Neon) with application schema `pd`
- Python 3.11+ using `psycopg[binary]`, `python-dotenv`, `faker`, `rapidfuzz`
- Read-only reporting views `pd.v_*` for safe dynamic SQL
- ETL canonicalizes school names, stores alias mappings, and queues uncertain cases
- AI-ready via pgvector embeddings (`pd.entity_embeddings`) and safe SQL guardrails

## Schema
- Core tables: accounts, contacts, applications, opportunities, experiences, work_experiences
- Engagement: opportunity_sponsorships, partner_engagements, outreach_messages
- ETL/AI: account_aliases, etl_school_name_review_queue, entity_embeddings, query_audit_log
- Views: `pd.v_*` mirror tables for reporting and dynamic SQL

## ETL
- Normalize now: lowercasing, noise removal, fuzzy matching (rapidfuzz)
- Store alias mappings: persist raw → canonical in `pd.account_aliases`
- Review queue: uncertain names to `pd.etl_school_name_review_queue`
- Batch API in `src/etl.py` with beginner-friendly comments

## AI-ready
- Vector search skeleton in `src/ai_demo.py` against `pd.entity_embeddings`
- Safe dynamic SQL in `src/safe_sql.py`: SELECT-only, `pd.v_*` views, enforced LIMIT
- Query auditing via `pd.query_audit_log`

## Data Export
- Export all `pd.*` tables to an Excel workbook: `report/data_export.xlsx`
- Script: `src/export_excel.py` (uses `openpyxl`)

Run:

```bash
source .venv/bin/activate
pip install -r requirements.txt  # ensure openpyxl installed
python -m src.export_excel
# Output: report/data_export.xlsx with sheets per table + summary_counts
```

## How to Run
1. Create `.env` from `.env.example` and set `DATABASE_URL`:

```bash
cp .env.example .env
# edit .env with your Neon connection string
```

2. Install dependencies (Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. (Optional) Create views and run safe SQL demo:

```bash
# Apply views in your database (ensure schema/tables exist)
psql "$DATABASE_URL" -f sql/02_views.sql

python src/ai_demo.py
```

4. Run the seed script (uses your `DATABASE_URL`):

```bash
# From project root
source .venv/bin/activate
python -m src.seed
```

Connectivity quick check:

```bash
python -c "from src.db import get_database_url; print(get_database_url()[:40])"
```
```

## Queries
- See `PD_Data_Architecture_Project/sql/03_questions.sql` for the 5 required questions.
- Use `src/safe_sql.py` for dynamic execution guarded by views and LIMIT.

## Screenshots
- Save evidence in `report/screenshots/` (folder pre-created).

## Notes
- Never hardcode credentials; all code reads `DATABASE_URL` from environment.
- Seed script is a skeleton; adjust column names/types to your actual schema before running.
- This repo is beginner-readable: short functions, clear comments, and minimal magic.
 
## Verification
The environment and data load were verified end-to-end:
- Schema accessible and views created (`sql/02_views.sql`).
- Seed executed via `python -m src.seed` with `.env` loading from project root.
- Row counts observed in `pd` tables after seed:
	- `pd.accounts`: 34
	- `pd.contacts`: 200
	- `pd.opportunities`: 10
	- `pd.opportunity_sponsorships`: 7
	- `pd.applications`: 230
	- `pd.experiences`: 180
	- `pd.work_experiences`: 180
	- `pd.partner_engagements`: 106
	- `pd.outreach_messages`: 120
	- `pd.account_aliases`: 5
	- `pd.etl_school_name_review_queue`: 4
	- `pd.entity_embeddings`: 0 (placeholder; to be populated by AI demo)
	- `pd.query_audit_log`: 0 (populated when `safe_sql` is used)

Quick re-verification:

```bash
source .venv/bin/activate
python - <<'PY'
from src.db import connect
tables = [
		'accounts','contacts','opportunities','opportunity_sponsorships',
		'applications','experiences','work_experiences','partner_engagements',
		'outreach_messages','account_aliases','etl_school_name_review_queue',
		'entity_embeddings','query_audit_log'
]
with connect() as conn, conn.cursor() as cur:
		for t in tables:
				cur.execute(f"select count(*) from pd.{t}")
				print(t, cur.fetchone()[0])
PY
```