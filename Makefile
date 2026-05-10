.PHONY: setup dev-backend dev-frontend install-backend install-frontend

setup:
	bash scripts/setup.sh

dev-backend:
	bash scripts/dev-backend.sh

dev-frontend:
	cd frontend && npm run dev

install-backend:
	backend/venv/bin/pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install
