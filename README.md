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

## Nullability Contract
- Acceptable nulls: optional fields like `contacts.email`, `contacts.phone`, `contacts.linkedin_url`, `experiences.end_date`, etc.
- Unacceptable nulls:
	- Primary keys in all tables (must be non-null)
	- Key foreign keys (must be non-null):
		- `work_experiences.company_account_id`
		- `applications.contact_id`, `applications.opportunity_id`
		- `experiences.contact_id`, `experiences.opportunity_id`
		- `opportunity_sponsorships.opportunity_id`
		- `partner_engagements.sponsor_account_id`
	- The seed enforces these; a post-seed assert fails if any `work_experiences.company_account_id` is null.

## End-to-end Pipeline
Run the complete pipeline and reporting:

```bash
source .venv/bin/activate
python -m src.seed
python -m src.data_quality
python -m src.eda_report
python -m src.export_excel
psql "$DATABASE_URL" -f sql/03_questions.sql
```

Outputs are written under `report/`:
- `report/null_profile.md`, `report/null_profile.csv`
- `report/quality_checks.md`
- `report/eda_report.md` + CSVs in `report/eda_csv/`
- `report/data_export.xlsx`
 - `report/csv/*.csv` (single source of truth for per-table CSVs)
 - `report/pd_tables.zip` (built only from `report/csv/*.csv`)

CSV Policy:
- All per-table CSVs live in `report/csv/` — use these only.
- Do NOT use or create CSVs directly under `report/`.
- The export script cleans up any legacy `report/*.csv` and zips `report/csv/*.csv` into `report/pd_tables.zip`.

## Data Pipeline Overview
Plain-text diagram of the flow:

```
Seed (src.seed)
	-> Data Quality (src.data_quality)
	-> EDA Summary (src.eda_report)
	-> Data Export (src.export_excel)
	-> Apply Views (sql/02_views.sql)
	-> Run Questions (sql/03_questions.sql)
```

## What `src/data_quality.py` Checks
- FK integrity: detects orphans where a foreign key points to a missing parent
- Duplicate logical keys: `applications(contact_id, opportunity_id)` should have at most one row per pair
- Unacceptable nulls: primary keys and key foreign keys
- Outputs:
	- `report/null_profile.md` + `report/null_profile.csv`
	- `report/quality_checks.md`

## What `src/eda_report.py` Produces
- Markdown tables (top summaries) and full CSVs for:
	- Contact types
	- Applications by status
	- Experiences by status
	- Top schools by applicant count
	- Placements by `industry_primary`
	- Sponsor funding totals
- Outputs:
	- `report/eda_report.md`
	- `report/eda_csv/*.csv`

## Acceptable vs Must-Not-Null (Per Table)
- `pd.accounts`:
	- Must-not-null: `account_id`, `account_type`, `name_canonical`
	- Acceptable-null: `website`, `linkedin_url`, `industry_primary`
- `pd.contacts`:
	- Must-not-null: `contact_id`, `contact_type`, `first_name`, `last_name`
	- Acceptable-null: `email`, `phone`, `linkedin_url`, `primary_school_account_id`
- `pd.applications`:
	- Must-not-null: `application_id`, `contact_id`, `opportunity_id`, `created_at`
	- Acceptable-null: `submitted_at`, `source_system`, `status`
- `pd.experiences`:
	- Must-not-null: `experience_id`, `contact_id`, `opportunity_id`, `status`
	- Acceptable-null: `notes`
- `pd.work_experiences`:
	- Must-not-null: `work_experience_id`, `contact_id`, `company_account_id`, `title`, `start_date`
	- Acceptable-null: `end_date`, `source_profile_url`, `source_payload`, `description`
- `pd.opportunity_sponsorships`:
	- Must-not-null: `sponsorship_id`, `opportunity_id`, `sponsor_display_name`, `sponsored_amount_usd`
	- Acceptable-null: `sponsor_account_id`
- `pd.partner_engagements`:
	- Must-not-null: `engagement_id`, `sponsor_account_id`, `engagement_date`, `engagement_type`
	- Acceptable-null: `notes`, `outcome`
- `pd.outreach_messages`:
	- Must-not-null: `message_id`, `sponsor_account_id`, `contact_id`, `channel`, `body`, `sent_at`
	- Acceptable-null: `subject`
- `pd.account_aliases`:
	- Must-not-null: `alias_id`, `account_id`, `alias_name`
	- Acceptable-null: `source_system`

## Why Some NULLs Are Realistic
- Form/CRM data is often incomplete: emails and phone numbers are optional; end dates may be unknown; social links may be missing.
- Sponsor account linkage can be absent for PD-sponsored programs; display name is used as a fallback.
- The seed enforces a Nullability Contract for key FKs (e.g., `work_experiences.company_account_id`) and checks are reported in `report/quality_checks.md`.

## Security & Secrets
- `.env` is ignored via `.gitignore` and not committed.
- Scripts read `DATABASE_URL` from environment; the README uses commands that only echo a truncated value.

Speed tips:
- You can lower the generated row counts by exporting env vars before running seed:

```bash
export N_CONTACTS=100 N_APPLICATIONS=120 N_EXPERIENCES=90 N_WORK_EXPERIENCES=90 N_OUTREACH=60 N_ENGAGEMENTS=45
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