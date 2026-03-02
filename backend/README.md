# AutoOps AI Backend

FastAPI + LangGraph service for tool-orchestrated workflows (Gemini LLM).

## Quickstart
1. Create virtualenv and install deps:
   ```bash
   /usr/bin/python3 -m pip install -r ../requirements.txt
   ```
2. Run dev server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Env vars (prefix `AUTOOPS_`):
   - `GEMINI_API_KEY` (required for LLM)
   - `DB_URL` (default sqlite+aiosqlite:///./autoops.db)
   - `ENV` (default local)

## Layout
- app/main.py: FastAPI entrypoint
- app/api: routers
- app/config.py: settings
- app/db: database setup
- app/models: ORM models
- app/schemas: Pydantic schemas
- app/tools: tool implementations
- app/workflows: LangGraph graphs
- tests: backend tests
