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

After the initial setup, start PostgreSQL, Ollama, the API, and the frontend with:

```sh
npm start
```

### Setup commands

Run individual setup steps when needed:

```sh
npm run ollama:setup     # Install/start Ollama and pull the configured model
npm run postgres:setup   # Install/start PostgreSQL on macOS or Ubuntu
npm run db:create        # Create the configured PostgreSQL user and database
npm run db:migrate       # Apply migrations and create/update PostgreSQL tables
npm run db:status        # Show the currently applied migration
npm run check            # Run lint, frontend build, and backend tests
```

Set `OLLAMA_MODEL` before `npm run ollama:setup` to install a different default model.

`DATABASE_URL` is required at runtime and must be provided in the root `.env`.
Database credentials are not hardcoded in the Python or Alembic configuration.

Add the application database credentials to `.env` as `POSTGRES_USER` and
`POSTGRES_PASSWORD`. For local Homebrew PostgreSQL, `POSTGRES_ADMIN_USER` can
usually remain empty. For a protected or remote server, also set the PostgreSQL
administrator username and password so `npm run db:create` can create the role
and database.

### Ubuntu first-time setup

On Ubuntu 24.04 or newer, install Git, curl, Python, and its virtual-environment
package first. Install Node.js 22 with your preferred Node version manager.
Then clone the repository and run:

```sh
cp .env.example .env
npm run setup
npm start
```

The setup command uses Ubuntu's package manager for PostgreSQL and Ollama's
official Linux installer. It may request `sudo` access while installing or
starting system services.

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

