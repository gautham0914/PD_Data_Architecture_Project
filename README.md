# PD Take-home: Data Architecture + Python ETL + AI-ready

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

## How to Run
1. Create `.env` from `.env.example` and set `DATABASE_URL`:

```bash
cp PD_Data_Architecture_Project/.env.example PD_Data_Architecture_Project/.env
# edit PD_Data_Architecture_Project/.env with your Neon connection string
```

2. Install dependencies (Python 3.11+):

```bash
python -m venv PD_Data_Architecture_Project/.venv
source PD_Data_Architecture_Project/.venv/bin/activate
pip install -r PD_Data_Architecture_Project/requirements.txt
```

3. (Optional) Create views and run safe SQL demo:

```bash
# Apply views in your database (ensure schema/tables exist)
psql "$DATABASE_URL" -f PD_Data_Architecture_Project/sql/02_views.sql

python PD_Data_Architecture_Project/src/ai_demo.py
```

4. Run the seed script (uses your `DATABASE_URL`):

```bash
# From project root
source PD_Data_Architecture_Project/.venv/bin/activate
python -m src.seed
```
```

## Queries
- See `PD_Data_Architecture_Project/sql/03_questions.sql` for the 5 required questions.
- Use `src/safe_sql.py` for dynamic execution guarded by views and LIMIT.

## Screenshots
- Save evidence in `PD_Data_Architecture_Projects/report/screenshots/` (folder pre-created).

## Notes
- Never hardcode credentials; all code reads `DATABASE_URL` from environment.
- Seed script is a skeleton; adjust column names/types to your actual schema before running.
- This repo is beginner-readable: short functions, clear comments, and minimal magic.