UV = UV_CACHE_DIR=.uv-cache uv
PYTEST = .venv/bin/python -m pytest -vv -s
UVICORN = .venv/bin/uvicorn

.PHONY: install test test-backend test-frontend build dev up e2e

install:
	$(UV) sync --dev
	npm install

test: test-backend test-frontend

test-backend:
	$(PYTEST)

test-frontend:
	npm test

build:
	npm run build

dev:
	$(UVICORN) backend.app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up --build

e2e:
	PYTHONPATH=. .venv/bin/python scripts/e2e_backend_smoke.py
	npm test
	npm run build
