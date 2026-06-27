#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="vigil-backend"
ENV_FILE="backend/.env"
EXAMPLE_FILE="backend/.env.example"

if [ -f "$ENV_FILE" ]; then
  echo "backend/.env already exists — skipping."
  echo "Delete it and re-run this script to regenerate from 1Password."
  exit 0
fi

if ! command -v op &>/dev/null; then
  echo "Warning: 1Password CLI (op) not found. Falling back to .env.example copy."
  echo "Install op with: brew install 1password-cli"
  echo "Then re-run this script to pull real secrets from 1Password."
  cp "$EXAMPLE_FILE" "$ENV_FILE"
  echo "Created backend/.env — fill in your values before starting the server."
  exit 0
fi

if ! op whoami &>/dev/null; then
  echo "Error: 1Password CLI is not signed in."
  echo "Open the 1Password app → Settings → Developer → enable 'Integrate with 1Password CLI'."
  exit 1
fi

echo "Pulling secrets from 1Password environment '$ENVIRONMENT'..."
op env get "$ENVIRONMENT" > "$ENV_FILE"
echo "backend/.env written from 1Password Environments."
