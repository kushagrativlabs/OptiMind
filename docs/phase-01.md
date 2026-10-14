# Phase 1 — Local Environment and Foundation

## Goal

Provide a working local application that connects a React interface to FastAPI, PostgreSQL, and Ollama.

## Included

- React, Vite, and TypeScript frontend
- FastAPI backend with versioned API routes
- PostgreSQL async connection configuration and status check
- Ollama model status check and chat endpoint
- Local PostgreSQL Compose service
- Responsive application shell with visible service health
- Backend health test and frontend lint/build checks

## Local services

| Service | Address | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:5173` | User interface |
| Backend | `http://localhost:8000` | API and API documentation |
| PostgreSQL | `localhost:5432` | Persistent application data |
| Ollama | `http://localhost:11434` | Local model inference |

## Completion checklist

- [x] Create the frontend and backend foundations.
- [x] Configure the backend for PostgreSQL.
- [x] Add Ollama readiness and chat integration.
- [x] Build the initial application layout.
- [x] Add setup and development documentation.
- [x] Install and start PostgreSQL 17 locally.
- [x] Start Ollama and install `qwen2.5:3b`.
- [x] Run an end-to-end chat request against the local model.

Phase 1 was validated end to end on October 14, 2026. The API reported all three
services online, and the browser chat successfully received a response from the
configured local model.

