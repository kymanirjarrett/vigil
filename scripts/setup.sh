#!/usr/bin/env bash
set -e

echo "→ Creating Python virtual environment..."
python3 -m venv backend/venv

echo "→ Installing Python dependencies..."
backend/venv/bin/pip install --quiet -r backend/requirements.txt

echo "→ Installing frontend dependencies..."
cd frontend && npm install --silent && cd ..

echo "→ Installing root dev tooling (Husky, lint-staged)..."
npm install --silent

echo ""
echo "✓ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. npm run reveal-secrets   — create your backend/.env"
echo "  2. npm run dev:backend      — start the API (terminal 1)"
echo "  3. npm run dev:frontend     — start the UI  (terminal 2)"
