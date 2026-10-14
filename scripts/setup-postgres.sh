#!/usr/bin/env bash

set -euo pipefail

operating_system="$(uname -s)"

case "${operating_system}" in
  Darwin)
    if ! brew list postgresql@17 >/dev/null 2>&1; then
      echo "Installing PostgreSQL 17 with Homebrew..."
      brew install postgresql@17
    fi
    brew services start postgresql@17 >/dev/null
    ;;
  Linux)
    if ! command -v psql >/dev/null 2>&1; then
      echo "Installing PostgreSQL from the Ubuntu package repository..."
      sudo apt-get update
      sudo apt-get install -y postgresql postgresql-client
    fi
    sudo systemctl enable --now postgresql
    ;;
  *)
    echo "Automatic PostgreSQL setup is supported on macOS and Ubuntu Linux."
    exit 1
    ;;
esac

echo "PostgreSQL is installed and running."

