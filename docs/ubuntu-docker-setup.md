# OptiMind on Ubuntu with Docker

This guide runs the OptiMind core stack in Docker:

- React/Vite frontend
- FastAPI backend
- PostgreSQL
- Ollama
- SearXNG web search

The database migrations run automatically when the backend container starts.

## 1. Install prerequisites

Install Ubuntu updates, Git, and Docker Engine with the Docker Compose plugin.
Then confirm Docker works:

```bash
docker --version
docker compose version
git --version
```

If Docker requires `sudo`, either prefix Docker commands with `sudo` or add your
user to the Docker group and sign in again:

```bash
sudo usermod -aG docker "$USER"
```

## 2. Download and configure OptiMind

```bash
git clone <your-repository-url> optimind
cd optimind
cp .env.docker.example .env
chmod 600 .env
```

Edit `.env` and set a strong database password and search secret. For a small
Ubuntu machine, use the lighter model:

```env
OLLAMA_MODEL=qwen2.5:1.5b
```

For a machine with more memory, the default `qwen2.5:3b` gives better answers.

## 3. Start the project

```bash
docker compose up -d --build
docker compose ps
```

Open the application on the Ubuntu machine at:

```text
http://localhost:5173
```

The first startup downloads the Ollama model and may take several minutes.
Follow startup logs with:

```bash
docker compose logs -f backend
```

Check the API and all dependencies:

```bash
curl http://localhost:8000/api/v1/status
```

## 4. Start automatically after Ubuntu reboots

The Compose services use `restart: unless-stopped`. Enable Docker at boot, then
start the stack once:

```bash
sudo systemctl enable --now docker
docker compose up -d
```

After a reboot, Docker automatically brings the containers back. Verify with:

```bash
docker compose ps
```

To stop the stack without deleting data:

```bash
docker compose down
```

To remove database and Ollama model data too (destructive):

```bash
docker compose down -v
```

## 5. Access from another office computer by static IP

Find the Ubuntu server's address:

```bash
hostname -I
```

If it returns `192.168.1.50`, open this from another computer on the same office
network:

```text
http://192.168.1.50:5173
```

If UFW is enabled, allow only the office LAN to reach the frontend:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 5173 proto tcp
sudo ufw status
```

Replace `192.168.1.0/24` with the actual office subnet. Do not expose ports
5432, 8000, 8080, or 11434 to the office or internet unless you have a specific
security reason.

## 6. Use an office hostname instead of an IP

Yes. The recommended approach is to create an internal DNS record in the office
router, Pi-hole, or Windows/AD DNS:

```text
optimind.office.example  ->  192.168.1.50
```

Then set the hostname allowed by Vite before starting the frontend:

```env
VITE_ALLOWED_HOSTS=optimind.office.example
```

Restart the frontend so it reads the setting:

```bash
docker compose up -d --build frontend
```

Users can then open:

```text
http://optimind.office.example:5173
```

For a quick office-only test without internal DNS, add the mapping to each
client computer's hosts file instead:

```text
192.168.1.50  optimind.office
```

Use the hostname in the browser:

```text
http://optimind.office:5173
```

For a polished permanent deployment, put Nginx or Caddy in front of the
frontend and use HTTPS. Do not expose the Vite development server directly to
the public internet.

## 7. Useful maintenance commands

```bash
docker compose logs -f                  # all services
docker compose restart backend         # restart only the API
docker compose pull                    # fetch newer images
docker compose up -d --build           # rebuild after code changes
docker compose down                     # stop containers
```
