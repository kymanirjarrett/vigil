#!/usr/bin/env bash
# Copies .env.example → .env so you can fill in real values.
# Can be upgraded to pull secrets from 1Password CLI (op read "op://vault/item/field")
# the same way enterprise repos do — just replace the cp with op inject commands.

if [ -f backend/.env ]; then
  echo "backend/.env already exists — skipping copy."
  echo "Edit it directly to update your secrets."
else
  cp backend/.env.example backend/.env
  echo "Created backend/.env from .env.example"
  echo "Open backend/.env and fill in your actual values before starting the server."
fi
