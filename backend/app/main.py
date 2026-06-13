from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.routers.evidence_packs import router as evidence_packs_router
from backend.app.routers.graph import router as graph_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.query import router as query_router
from backend.app.routers.results import router as results_router
from backend.app.routers.scan import router as scan_router

app = FastAPI(
    title="DevOnboard API",
    description="Local codebase institutional-memory API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)
app.include_router(ingest_router)
app.include_router(graph_router)
app.include_router(query_router)
app.include_router(evidence_packs_router)
app.include_router(results_router)


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    graph_repo = None
    if settings.devonboard_graph_path.exists():
        try:
            graph_repo = GraphStore.load(settings.devonboard_graph_path).graph.repo.model_dump()
        except Exception:
            graph_repo = None
    return {
        "status": "ok",
        "graph_exists": settings.devonboard_graph_path.exists(),
        "qdrant": bool(settings.qdrant_url),
        "llm_available": bool(settings.gemini_api_key),
        "target_repo": {
            "path": str(settings.target_repo_path),
            "branch": settings.target_repo_branch,
            "commit": settings.target_repo_commit,
        },
        "graph_repo": graph_repo,
    }
