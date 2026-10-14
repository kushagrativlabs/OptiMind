#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${project_root}/.env"

if [[ ! -f "${env_file}" ]]; then
  echo "Missing ${env_file}. Copy .env.example to .env and add your database settings."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a

app_db="${POSTGRES_DB:?POSTGRES_DB is required in .env}"
app_user="${POSTGRES_USER:?POSTGRES_USER is required in .env}"
app_password="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in .env}"
db_host="${POSTGRES_HOST:-localhost}"
db_port="${POSTGRES_PORT:-5432}"
admin_user="${POSTGRES_ADMIN_USER:-}"
admin_password="${POSTGRES_ADMIN_PASSWORD:-}"

psql_bin="$(command -v psql || true)"
if [[ -z "${psql_bin}" && -x /opt/homebrew/opt/postgresql@17/bin/psql ]]; then
  psql_bin="/opt/homebrew/opt/postgresql@17/bin/psql"
fi

if [[ -z "${psql_bin}" ]]; then
  echo "PostgreSQL client not found. Install PostgreSQL before creating the database."
  exit 1
fi

echo "Creating PostgreSQL role and database when missing..."
if [[ "$(uname -s)" == "Linux" && -z "${admin_user}" && -z "${admin_password}" ]]; then
  psql_command=(sudo -u postgres "${psql_bin}" --dbname postgres)
else
  admin_user="${admin_user:-$(id -un)}"
  psql_command=(
    "${psql_bin}"
    --host "${db_host}"
    --port "${db_port}"
    --username "${admin_user}"
    --dbname postgres
  )
fi

PGPASSWORD="${admin_password}" "${psql_command[@]}" \
  --set ON_ERROR_STOP=1 \
  --set app_db="${app_db}" \
  --set app_user="${app_user}" \
  --set app_password="${app_password}" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec

SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_user', :'app_password') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'app_db', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'app_db') \gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', :'app_db', :'app_user') \gexec
SQL

echo "Database ${app_db} and role ${app_user} are ready."

