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

### Ubuntu with Docker (recommended)

For the full Ubuntu installation, automatic startup, static-IP access, and an
internal office hostname, see [docs/ubuntu-docker-setup.md](docs/ubuntu-docker-setup.md).

This runs the complete core stack in containers: PostgreSQL, Ollama, SearXNG,
the FastAPI backend, and the Vite frontend. Docker Compose creates the database
tables automatically when the backend starts. Image generation remains disabled
by default because its CPU/GPU runtime is hardware-specific; enable it later
with a separate image-generation service if needed.

Install Docker Engine and the Compose plugin on Ubuntu, then run:

```sh
git clone <your-repository-url> optimind
cd optimind
cp .env.docker.example .env
chmod 600 .env
docker compose up -d --build
docker compose logs -f backend
```

Open <http://localhost:5173>. The first start downloads the configured Ollama
model and can take several minutes. Check the services with:

```sh
docker compose ps
curl http://localhost:8000/api/v1/status
```

#### Access from another computer using the Ubuntu static IP

The frontend is published on all host interfaces, so use the Ubuntu machine's
static/private IP from another device on the same network:

```sh
hostname -I
# Example: http://192.168.1.50:5173
```

Open `http://YOUR_UBUNTU_IP:5173` in the other computer's browser. If UFW is
enabled, allow only your private network to reach the frontend:

```sh
sudo ufw allow from 192.168.1.0/24 to any port 5173 proto tcp
sudo ufw status
```

Replace `192.168.1.0/24` with your actual LAN range. Do not expose port 8000,
5432, 8080, or Ollama's port to the public internet. For access outside your
LAN, use a VPN or a reverse proxy with HTTPS and authentication rather than
forwarding the development server directly.

To stop the project without deleting data:

```sh
docker compose down
```

To remove the database and Ollama model volumes as well, use
`docker compose down -v`. This permanently deletes those local Docker volumes.

### Run two chats at the same time

OptiMind defaults to two parallel Ollama requests, which is suitable for a
16 GB computer when using the lightweight models. On macOS, apply the setting
once and restart the Ollama app:

```sh
npm run ollama:configure
```

On Ubuntu, add `OLLAMA_NUM_PARALLEL=2` and `OLLAMA_MAX_LOADED_MODELS=1` to the
Ollama systemd service environment, then restart it with
`sudo systemctl restart ollama`. Increasing parallelism uses more RAM; keep it
at 2 on a 16 GB system.

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

Set `OLLAMA_MODEL` before `npm run ollama:setup` to install a different default
text model. Set `OLLAMA_VISION_MODEL` to choose the model used for image analysis.

### Image analysis

Select a model marked **Vision** in the model picker, then use the image button
beside the message box. OptiMind accepts up to three JPEG, PNG, or WebP images,
with a maximum size of 5 MB each. Attachments are stored with the conversation
and restored when chat history is reopened. The default lightweight vision model
is `qwen3.5:0.8b`.

### Local image generation

OptiMind can generate images locally through `stable-diffusion.cpp` using the
free quantized LCM-SSD-1B model. It has stronger SDXL-based prompt adherence
than the earlier Stable Diffusion 1.5 model while remaining CPU-friendly. Install it once:

```sh
npm run image:setup
```

Set `IMAGE_GENERATION_ENABLED=true` in `.env`, then use `npm start`. The main
startup command starts the image service automatically. In the chat, turn on
the **Image** pill, describe the image, and send the prompt. The generated PNG
is stored in chat history and includes a download link.

Put wording that must be spelled exactly inside quotation marks, for example
`a neon sign that says "MIDNIGHT CAFE"`. OptiMind generates the scene locally
and then renders the quoted wording itself because diffusion models are not
reliable text spellers.

The default is 512×512 with four LCM steps. It uses a separate SDXL VAE so the
Q4 model decodes images reliably.
`IMAGE_GENERATION_BACKEND=cpu` is the safe default for Ubuntu and also avoids
white-image numerical failures seen with some Metal/Q4 combinations. Keep the
LCM model at four steps unless you intentionally test different sampling
settings. Image generation is substantially slower than chat on CPU-only systems.

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

On another device connected to the same private network, open:

```text
http://UBUNTU_SERVER_IP:5173
```

Find the Ubuntu server's address with `hostname -I`. Do not use `localhost`
from another computer because that refers to the computer running the browser.
If Ubuntu's firewall is enabled, allow private-network access to the frontend
port with `sudo ufw allow 5173/tcp`.

The frontend development server forwards `/api` requests to FastAPI at `http://localhost:8000`.

### Webpage summaries and questions

Paste a public URL or a domain such as `sample.com` into a conversation. OptiMind
downloads the readable page text and, for a homepage, follows up to eight internal
same-domain pages across two link levels. It asks the selected Ollama model to
summarize the collected content and uses it as reference context for follow-up
questions in the same conversation.
Private-network and localhost URLs are blocked, downloads are size-limited, and
page content is treated as untrusted reference data rather than instructions.

### Current web search for SEO, AEO, and GEO

OptiMind uses a private SearXNG container to research current search results and
pass them to either a local or cloud Ollama model with source URLs. No account,
API key, subscription, or per-search payment is required. Enable it in `.env`:

```env
WEB_SEARCH_ENABLED=true
SEARXNG_BASE_URL=http://localhost:8080
```

Install/start the local search service with `npm run web-search:setup`, restart
OptiMind, and enable **Web search** beside the model selector. Search-result
content is treated as untrusted reference data, and the model is instructed to
cite its sources. SearXNG is bound to localhost and is not exposed to the network.

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

node --version
npm --version
curl -I http://127.0.0.1:5173
ss -ltnp | grep 5173
