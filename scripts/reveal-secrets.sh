#!/usr/bin/env bash
set -euo pipefail

VAULT="Vigil"
ITEM="vigil-backend-env"
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

echo "Pulling secrets from 1Password vault '$VAULT' / item '$ITEM'..."

op read "op://$VAULT/$ITEM/AWS_ACCESS_KEY_ID" > /dev/null 2>&1 || {
  echo "Error: Could not reach 1Password. Run 'op signin' and try again."
  exit 1
}

cat > "$ENV_FILE" <<EOF
AWS_ACCESS_KEY_ID=$(op read "op://$VAULT/$ITEM/AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=$(op read "op://$VAULT/$ITEM/AWS_SECRET_ACCESS_KEY")
AWS_REGION=$(op read "op://$VAULT/$ITEM/AWS_REGION")
SENDGRID_API_KEY=$(op read "op://$VAULT/$ITEM/SENDGRID_API_KEY")
ALERT_SENDER_EMAIL=$(op read "op://$VAULT/$ITEM/ALERT_SENDER_EMAIL")
DATABASE_URL=$(op read "op://$VAULT/$ITEM/DATABASE_URL")
VIGIL_JWT_SECRET=$(op read "op://$VAULT/$ITEM/VIGIL_JWT_SECRET")
VIGIL_ADMIN_EMAIL=$(op read "op://$VAULT/$ITEM/VIGIL_ADMIN_EMAIL")
VIGIL_ADMIN_PASSWORD=$(op read "op://$VAULT/$ITEM/VIGIL_ADMIN_PASSWORD")
ALLOWED_ORIGINS=$(op read "op://$VAULT/$ITEM/ALLOWED_ORIGINS")
EOF

echo "backend/.env written from 1Password."
