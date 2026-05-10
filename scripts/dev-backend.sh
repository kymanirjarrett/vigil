#!/usr/bin/env bash
set -e

# Activate the venv created by setup.sh
source backend/venv/bin/activate

cd backend
uvicorn main:app --reload
