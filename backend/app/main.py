from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.models import KnowledgeGraph
from backend.app.routers.evidence_packs import router as evidence_packs_router
from backend.app.routers.graph import router as graph_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.query import router as query_router
from backend.app.routers.results import router as results_router
from backend.app.routers.scan import router as scan_router

_graph_cache: KnowledgeGraph | None = None

def get_cached_graph() -> KnowledgeGraph | None:
    return _graph_cache

def set_cached_graph(graph: KnowledgeGraph) -> None:
    global _graph_cache
    _graph_cache = graph

def invalidate_graph_cache() -> None:
    global _graph_cache
    _graph_cache = None

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
    graph = get_cached_graph()
    if graph is not None:
        graph_repo = graph.repo.model_dump()
    elif settings.devonboard_graph_path.exists():
        try:
            graph = GraphStore.load(settings.devonboard_graph_path).graph
            set_cached_graph(graph)
            graph_repo = graph.repo.model_dump()
        except Exception:
            graph_repo = None
    return {
        "status": "ok",
        "graph_exists": settings.devonboard_graph_path.exists(),
        "qdrant": {
            "configured": bool(settings.qdrant_url),
            "integrated": False,  # Qdrant vector search not yet implemented; graph-first retrieval is active
            "url": settings.qdrant_url if settings.qdrant_url else None,
        },
        "llm_available": bool(settings.gemini_api_key),
        "target_repo": {
            "path": str(settings.target_repo_path),
            "branch": settings.target_repo_branch,
            "commit": settings.target_repo_commit,
        },
        "graph_repo": graph_repo,
    }

