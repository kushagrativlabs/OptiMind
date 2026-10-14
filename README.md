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
3. Start Ollama and download the model with `ollama pull qwen2.5:3b`.
4. Set up and run the backend:

   ```sh
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e '.[dev]'
   uvicorn app.main:app --reload
   ```

5. In another terminal, run the frontend:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

6. Open <http://localhost:5173>.

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

