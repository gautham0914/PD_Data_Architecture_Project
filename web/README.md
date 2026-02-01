# Web Static Demo

This folder contains a read-only, static demo site for the PD Data Architecture Project.

## Assets to Provide
Place the following images under `web/assets/`:

- Branding:
  - `pd_logo-no_bg.png` — the Project Destined logo (transparent/no background)
  - `development_image.png` — a development/learning-focused hero image used on the page
- Schema:
  - `schema_diagram.png` — database schema diagram
- SQL Results:
  - `q1.png`, `q2.png`, `q3_1.png`, `q3_2.png`, `q3_3.png`, `q4_1.png`, `q4_2.png`, `q5_1.png`, `q5_2.png`
- AI/LLM Proofs:
  - `embeddings.png`, `ai_ready.png`, `llm_sql.png`, `llm_question.png`
- Optional:
  - `hero.png` — if you prefer a different header image (we currently use `community.jpg`)

## Deploy on Vercel

1. Install and login:
```bash
npm i -g vercel
vercel login
```
2. Deploy from `web/`:
```bash
vercel --cwd web
vercel --cwd web --prod
```

Alternatively, use Vercel dashboard and set Root Directory to `web`.

## Local API Demo (Serverless)

- Ensure `DATABASE_URL` is set in your environment (Neon Postgres). Optionally set `API_TOKEN`.
- Vercel CLI can run serverless functions locally:

```bash
vercel login
vercel dev
# Open http://localhost:3000/web/index.html
```

Environment variables on Vercel:
- `DATABASE_URL`: Neon connection string
- `API_TOKEN` (optional): if set, requests must include `x-api-token` header

Endpoints:
- `POST /api/query` {"query_id": "q1_cbre_boston_completed" | ...}
- `POST /api/canonicalize` {"raw_name": "Hofstra Univ"}
