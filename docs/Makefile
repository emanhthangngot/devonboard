.PHONY: help setup ingest dev up down benchmark test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Clone pinned demo repo and create .env
	@echo "→ Cloning prepared demo repo..."
	@if [ ! -d "target_repo" ]; then \
		git clone -b dev https://github.com/nextlevelbuilder/goclaw target_repo/; \
	else \
		echo "  target_repo/ already exists, skipping clone"; \
	fi
	@if [ -n "$$TARGET_REPO_COMMIT" ]; then \
		cd target_repo && git checkout "$$TARGET_REPO_COMMIT"; \
	fi
	@echo "→ Creating .env from .env.example..."
	@if [ ! -f ".env" ]; then cp .env.example .env; echo "  Created .env — fill in GEMINI_API_KEY"; fi
	@echo "✓ Setup complete. Edit .env with your API keys, then run: make ingest"

ingest: ## Run DevOnboard scan + history ingest into knowledge graph
	@echo "→ Running DevOnboard structure scan..."
	cd backend && pip install -r requirements.txt -q && \
		python -m app.scan.run --repo ../target_repo
	@echo "→ Running history ingest..."
	cd backend && python -m app.ingest.run --repo ../target_repo --max-commits 500
	@echo "✓ Ingest complete. Check devonboard/knowledge-graph.json"

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

clean: ## Remove optional Qdrant data, generated graph, benchmark results
	@echo "→ Stopping and removing Qdrant container..."
	docker stop qdrant && docker rm qdrant || true
	@echo "→ Removing generated graph..."
	rm -f devonboard/knowledge-graph.json
	@echo "→ Clearing benchmark results..."
	rm -f benchmark/results/*.json
	@echo "✓ Clean complete (target_repo/ kept, re-run 'make ingest' to rebuild)"
