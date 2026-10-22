# Vercel Hobby deployment

The repository root contains the full-stack Vercel configuration. Use the repository root as the project's Root Directory, not `frontend`. The build installs and builds the Vite frontend; `/api/v1/*` and `/health/*` are routed to the Python FastAPI function.

## Required environment

- `DATABASE_URL`: Neon pooled PostgreSQL connection, injected by the Marketplace integration.
- `DATABASE_URL_UNPOOLED`: direct connection for migrations, injected by Neon.
- `SECRET_KEY`: generated random secret, saved in Vercel as a Secret.
- `LLM_API_KEY`: Groq API key, stored only in Vercel's backend environment.
- Optional `LLM_MODEL`: defaults to `llama-3.3-70b-versatile`; select a model available to the Groq account.

The API entry point selects inline ingestion, ONNX BGE embeddings, temporary extraction/cache directories under `/tmp`, and the Groq provider. It does not use Redis or a continuously running Celery process. The Docker deployment continues using its existing worker mode.

Source file contents, chunks, embeddings, accounts, projects, conversations, and citations persist in Neon PostgreSQL. Uploaded ZIPs are used temporarily and removed after indexing; the original ZIP is not retained as a downloadable artifact.

## Hobby limits

- ZIP upload: 4 MB, below Vercel's 4.5 MB request limit after multipart overhead.
- Extraction: 10 MB.
- Source files: 100 per project.
- Indexed chunks: 300 per project.
- Function duration: 300 seconds. The first upload or search on a cold instance downloads the public embedding model. Small sample repositories are the intended workload.
- Optional cross-encoder reranking falls back to the normal hybrid ranking because the larger PyTorch runtime is excluded.
- Neon and Groq Free quotas apply. Do not enable paid upgrades, model credit top-ups, or a paid Groq plan for this deployment.

## Release procedure

From a checkout explicitly linked to the intended Vercel team and project:

```powershell
vercel env pull .env.local --yes --environment production
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe scripts/migrate_vercel.py
vercel deploy --prod --skip-domain
.venv/Scripts/python.exe scripts/verify_deployment.py --url https://THE_STAGED_ALIAS --force-upload
vercel promote https://THE_TESTED_DEPLOYMENT
```

Migrations use the direct connection and are recorded in Alembic. Apply them before releasing application code that needs a new schema. Avoid automatically running migrations on every cold start.

`scripts/verify_deployment.py` checks real registration/login, invalid credentials, indexing, persisted files, semantic retrieval, cross-user access rejection, and a model answer with citations. `--local` uses the same entry point with TestClient against the linked database. `--skip-chat` only checks the non-generation features; it is not evidence that chat is configured. Generated smoke-test credentials stay in ignored `.local-demo.json` and must not be committed.

Never expose database credentials, JWT secrets, or the Groq key through `VITE_*` variables. `.env.local` and `.vercel` are ignored, and `.vercelignore` excludes local secrets and virtual environments from uploads.
