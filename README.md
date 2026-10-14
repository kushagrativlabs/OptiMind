# OptiMind

OptiMind is a local-first AI colleague for managing and improving WordPress websites. Phase 1 provides a React application shell, a FastAPI backend, PostgreSQL configuration, and an Ollama chat connection.

## Prerequisites

- Node.js 22+
- Python 3.12+
- Ollama
- Docker Desktop, Docker Engine, or a local PostgreSQL installation

## Quick start

1. Copy `.env.example` to `.env`.
2. Start PostgreSQL with `docker compose -f infrastructure/compose.yaml up -d` or provide your own `DATABASE_URL`.
3. Install dependencies, ensure Ollama and Qwen are ready, and create/update the database tables:

   ```sh
   npm run setup
   ```

4. Run the backend:

   ```sh
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload
   ```

5. In another terminal, run the frontend:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

6. Open <http://localhost:5173>.

### Setup commands

Run individual setup steps when needed:

```sh
npm run ollama:setup     # Install/start Ollama and pull the configured model
npm run db:migrate       # Apply migrations and create/update PostgreSQL tables
npm run db:status        # Show the currently applied migration
npm run check            # Run lint, frontend build, and backend tests
```

Set `OLLAMA_MODEL` before `npm run ollama:setup` to install a different default model.

`DATABASE_URL` is required at runtime and must be provided in the root `.env`.
Database credentials are not hardcoded in the Python or Alembic configuration.

The frontend development server forwards `/api` requests to FastAPI at `http://localhost:8000`.

## Useful checks

```sh
cd backend && pytest
cd frontend && npm run lint && npm run build
```

API documentation is available at <http://localhost:8000/docs> while the backend is running.

## Project layout

```text
frontend/       React, Vite, and TypeScript
backend/        FastAPI application and tests
infrastructure/ Local and production service configuration
docs/           Project documentation
```

