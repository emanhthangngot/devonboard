.PHONY: help setup ingest dev up down benchmark test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Clone goclaw, install CodeGraph, create .env
	@echo "→ Cloning goclaw..."
	@if [ ! -d "target_repo" ]; then \
		git clone -b dev https://github.com/nextlevelbuilder/goclaw target_repo/; \
	else \
		echo "  target_repo/ already exists, skipping clone"; \
	fi
	@echo "→ Installing CodeGraph CLI..."
	npm install -g @colbymchenry/codegraph
	@echo "→ Initializing CodeGraph index (this takes ~3-5 min for goclaw)..."
	cd target_repo && codegraph init -i
	@echo "→ Creating .env from .env.example..."
	@if [ ! -f ".env" ]; then cp .env.example .env; echo "  Created .env — fill in GEMINI_API_KEY"; fi
	@echo "✓ Setup complete. Edit .env with your API keys, then run: make ingest"

ingest: ## Run git history + GitHub API ingest into Qdrant
	@echo "→ Starting Qdrant (if not running)..."
	@docker start qdrant 2>/dev/null || docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
	@echo "→ Running ingest pipeline..."
	cd backend && pip install -r requirements.txt -q && \
		python -m app.ingest.run --max-commits 500
	@echo "✓ Ingest complete. Check Qdrant at http://localhost:6333/dashboard"

dev: ## Start backend + frontend in watch mode (no Docker)
	@echo "→ Starting backend (port 8000)..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "→ Starting frontend (port 3000)..."
	cd frontend && npm run dev

up: ## Start all services via Docker Compose
	docker compose up --build

down: ## Stop all services
	docker compose down

benchmark: ## Run 5-query benchmark comparison, save to benchmark/results/
	@echo "→ Running benchmark (DevOnboard vs plain Gemini agent)..."
	@echo "  This runs 10 API calls and takes ~3-4 minutes (rate limit: 15 RPM)"
	cd backend && python -m app.benchmark.run
	@echo "✓ Results saved to benchmark/results/"
	@ls -la benchmark/results/

test: ## Run backend tests + frontend type-check
	@echo "→ Backend tests..."
	cd backend && pytest tests/ -v
	@echo "→ Frontend type-check..."
	cd frontend && npx tsc --noEmit

clean: ## Remove Qdrant data, CodeGraph index, benchmark results
	@echo "→ Stopping and removing Qdrant container..."
	docker stop qdrant && docker rm qdrant || true
	@echo "→ Removing CodeGraph index..."
	rm -rf target_repo/.codegraph/
	@echo "→ Clearing benchmark results..."
	rm -f benchmark/results/*.json
	@echo "✓ Clean complete (target_repo/ kept, re-run 'make setup' to re-index)"
