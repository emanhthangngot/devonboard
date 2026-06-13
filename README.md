# DevOnboard

**AI codebase onboarding with cited institutional memory.**

DevOnboard scans a repository, ingests development history, extracts design rationale, and builds a local knowledge graph that answers how the code works, why it was designed that way, and what risks matter before refactoring.

---

## Folder Structure

```text
├── 00_problem_statement.md   # Core problem definition
├── 01_market_and_domain/      # Market/competitor landscape analysis
├── 02_theme_deep_dive/        # Technical theme and challenges
├── 03_target_users/           # Target persona definitions
├── 04_case_studies/           # Case studies on existing codebases
├── 05_use_cases/              # Core product use cases
├── devonboard-design/         # Design system, UX flows, accessibility, and UI components
├── docs/                      # Architectural specifications, diagrams, plans, and API docs
├── backend/                   # FastAPI Python backend (scanner, ingest, query, benchmark)
├── frontend/                  # Next.js workspace user interface
├── scripts/                   # Integration and verification scripts
├── Makefile                   # Automation commands for dependencies, tests, running, and E2E
├── package.json               # Frontend dependencies and scripts
└── pyproject.toml             # Backend dependencies (managed via uv)
```

---

## Requirements & Prerequisites

Ensure the following tools are installed on your system:

- **Git** (for repository scanning and version history retrieval)
- **Python >= 3.11** (FastAPI backend)
- **uv** (recommended for fast Python package resolution and virtualenv sync)
- **Node.js >= 22** & **npm** (Next.js frontend)
- **Docker & Docker Compose** (optional, for Qdrant database or fully-containerized deployment)

---

## Configuration (`.env`)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and fill in:
   - `GEMINI_API_KEY`: Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey). Required for Q&A synthesis and rationale extraction.
   - `GITHUB_TOKEN`: Recommended. Increases GitHub API rate limits from 60 to 5000 requests/hour (read-only `public_repo` scope needed).
   - Configure other settings like `TARGET_REPO_PATH` (defaults to `./target_repo`).

---

## Fixture Repository Setup

The DevOnboard MVP is designed to run against a target repository. The prepared fixture is `goclaw`:

```bash
git clone https://github.com/nextlevelbuilder/goclaw target_repo
```

---

## Building and Running the Application

You can build and run the application either **locally (bare metal)** or using **Docker Compose**.

### Option A: Local Development (Bare Metal)

Using the root `Makefile` is the recommended way to manage dependencies and servers:

1. **Install Dependencies**:
   ```bash
   make install
   ```
   *This syncs Python dependencies using `uv` (creates a `.venv` virtual environment) and installs Node.js packages using `npm install`.*

2. **Run the Backend API**:
   ```bash
   make dev
   ```
   *Starts the FastAPI backend at `http://localhost:8000` with hot-reloading (via Uvicorn).*

3. **Run the Frontend UI**:
   In a separate terminal tab/window, start the Next.js development server:
   ```bash
   npm run dev
   ```
   *Starts the React user interface at `http://localhost:3000`.*

---

### Option B: Containerized Run (Docker Compose)

To build and launch all services (FastAPI backend, Next.js frontend, and a Qdrant vector database) in containers:

```bash
make up
# Or: docker compose up --build
```

Access the web interface at `http://localhost:3000` once the services are running.

---

## Verification & Testing

Verify that both frontend and backend are functional by running the test suite:

- **Run all tests** (Python + Vitest):
  ```bash
  make test
  ```
- **Backend tests only** (Pytest):
  ```bash
  make test-backend
  ```
- **Frontend tests only** (Vitest):
  ```bash
  make test-frontend
  ```
- **Run the E2E backend smoke test and build pipeline**:
  ```bash
  make e2e
  ```

---

## Core Product Walkthrough

Once the app is running:

1. **Scan the Codebase**: In the top navigation of the UI, click **Run Scan**. This walks the target repository and populates the structural graph.
2. **Ingest Git History**: Click **Ingest History** to extract git commit logs, link them to modules/classes/functions, and query design-rationale claims.
3. **Inspect the Graph**: Click on files or nodes in the left panel to open them in the **History/Why Inspector** on the right, which shows associated authors, risks, claims, and commits.
4. **Ask Cited Q&A**: Enter a query in the central panel (e.g., *"How does the agent pipeline execute a tool call?"*). The system will search the graph, retrieve evidence, use Gemini to synthesize an answer, and list citations linked directly to raw commits and files.
5. **Run Evaluation Benchmarks**: Go to `/benchmark` (or click "Benchmark" in the top bar) and click **Run Benchmark** to evaluate retrieval quality and latency against standard LLM baselines.
6. **Generate Evidence Packs**: Generate copyable Markdown guides customized for PR reviews or coding agents.

---

## Documentation Index

- Detailed Backend Design: [docs/BACKEND.md](docs/BACKEND.md)
- Detailed Frontend & UX Specs: [docs/FRONTEND.md](docs/FRONTEND.md)
- AI & Ingestion Pipelines: [docs/AI.md](docs/AI.md)
- RAG & Graph Retrieval details: [docs/RAG.md](docs/RAG.md)
- Architecture Overview: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Design Specifications: [devonboard-design/DESIGN.md](devonboard-design/DESIGN.md)
