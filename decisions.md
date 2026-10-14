# OptiMind Decisions

This document records the key product, architecture, infrastructure, and delivery decisions for OptiMind. Update it whenever a significant decision is made or changed.

## Decision status

- **Accepted** — approved and ready to use.
- **Proposed** — recommended but not yet confirmed.
- **Deferred** — intentionally postponed.
- **Superseded** — replaced by a newer decision.

## Accepted decisions

### D-001 — Develop locally before production deployment

- **Status:** Accepted
- **Decision:** Build and test OptiMind locally on macOS before deploying it to the Ubuntu Server iMac.
- **Reason:** This keeps early development isolated from the production machine and makes iteration safer.

### D-002 — Use a React and TypeScript frontend

- **Status:** Accepted
- **Decision:** Build the frontend with React, Vite, and TypeScript.
- **Reason:** This provides a fast development workflow, type safety, and a mature component ecosystem.

### D-003 — Use FastAPI for the backend

- **Status:** Accepted
- **Decision:** Build the backend with Python and FastAPI.
- **Reason:** FastAPI supports typed APIs, asynchronous workloads, and straightforward integration with Python AI tooling.

### D-004 — Run the initial AI model locally

- **Status:** Accepted
- **Decision:** Use Ollama with Qwen2.5 3B as the initial local model.
- **Reason:** A small local model supports privacy, avoids per-request API costs, and is suitable for initial development and CPU-based deployment testing.

### D-005 — Use PostgreSQL for persistent data

- **Status:** Accepted
- **Decision:** Store application data, website configurations, conversations, permissions, audit results, and history in PostgreSQL.
- **Reason:** The application requires reliable relational storage and structured querying.

### D-006 — Use Redis and Celery for background work

- **Status:** Accepted
- **Decision:** Use Redis as the broker and Celery for scheduled and long-running background jobs.
- **Reason:** Website crawls, audits, reports, and automated tasks should not block interactive API requests.

### D-007 — Integrate websites through WordPress and SFTP

- **Status:** Accepted
- **Decision:** Use the WordPress REST API for supported content operations and SFTP for approved file-level access.
- **Reason:** The two interfaces cover both managed WordPress content and controlled access to files that the REST API cannot handle.

### D-008 — Enforce explicit permission modes

- **Status:** Accepted
- **Decision:** Support Read Only, Ask Before Changes, Auto Edit, and Full Access modes at the website level.
- **Reason:** The agent's autonomy must be transparent, limited, and configurable for each website.

### D-009 — Preserve changes and make them reversible

- **Status:** Accepted
- **Decision:** Keep backups, diffs, audit logs, validation results, and rollback support for website changes.
- **Reason:** AI-generated modifications must be reviewable and recoverable.

### D-010 — Deliver the product in eight phases

- **Status:** Accepted
- **Decision:** Follow the phased delivery plan: foundation, agent system, website management, audits, integrations, permissions, automation, and deployment.
- **Reason:** The order establishes core dependencies before adding higher-risk automation and production access.

## Current development environment

Checked on October 14, 2026:

| Component | Current state |
| --- | --- |
| macOS architecture | Apple Silicon (`arm64`) |
| Python | 3.14.6 installed |
| Node.js | 22.14.0 installed |
| npm | 10.9.2 installed |
| PostgreSQL | 17.11 installed and running through Homebrew |
| Ollama | Client 0.40.3 running with `qwen2.5:3b` installed |
| Docker | Not installed |
| Project directory | Git monorepo initialized with frontend, backend, infrastructure, and docs |

## Proposed decisions requiring confirmation

### D-011 — Supported Python version

- **Status:** Accepted
- **Decision:** Support Python 3.12 and newer; Phase 1 is validated on Python 3.14.
- **Reason:** The selected Phase 1 dependencies install and pass the test suite on Python 3.14 while retaining compatibility with Python 3.12 for production.

### D-012 — Local service management

- **Status:** Accepted
- **Decision:** Run PostgreSQL through Homebrew and run Ollama directly on macOS during early development. Keep Docker Compose configuration available for reproducible environments and later deployment.
- **Reason:** PostgreSQL and Ollama can run locally now without requiring Docker Desktop; Compose remains an optional path.

### D-013 — Repository layout

- **Status:** Accepted
- **Decision:** Use one Git repository containing `frontend`, `backend`, `infrastructure`, and `docs` directories.
- **Reason:** A monorepo simplifies coordinated changes, local setup, and deployment for the initial team and MVP.

### D-014 — Backend database stack

- **Status:** Accepted
- **Decision:** Use SQLAlchemy 2 with the async PostgreSQL driver. Add Alembic when the first persistent model is introduced.
- **Reason:** This provides async compatibility with FastAPI without adding migration scaffolding before a schema exists.

### D-015 — Frontend styling and component system

- **Status:** Accepted
- **Decision:** Use custom CSS for the Phase 1 shell and defer choosing a component library until the Phase 2 interaction requirements are established.
- **Reason:** The initial interface is small enough to remain dependency-light while preserving the option to adopt a reusable component system later.

### D-016 — Authentication model

- **Status:** Proposed
- **Recommendation:** Decide whether the MVP is single-user on a private network or supports multiple authenticated team members.
- **Reason:** This affects the data model, permissions, audit attribution, API security, and deployment configuration.

### D-017 — Secrets storage

- **Status:** Proposed
- **Recommendation:** Encrypt WordPress and SFTP credentials at rest and keep encryption keys outside the database.
- **Reason:** Website credentials must never be stored as readable application data.

### D-018 — Production container architecture

- **Status:** Deferred
- **Decision needed:** Confirm whether all services will run in containers on the Ubuntu iMac or whether Ollama will run directly on the host.
- **Reason:** The best choice depends on hardware acceleration, operational simplicity, and the final Ubuntu configuration.

## Decision template

Copy this section when adding a decision:

```markdown
### D-XXX — Decision title

- **Status:** Proposed | Accepted | Deferred | Superseded
- **Decision:** What was decided.
- **Reason:** Why this choice was made.
- **Consequences:** Important tradeoffs or follow-up work.
- **Supersedes:** Previous decision ID, if applicable.
```
