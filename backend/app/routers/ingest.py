import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.ingest.git_extractor import GitHistoryIngestor
from backend.app.services.repo_resolver import resolve_repository_input

router = APIRouter()

_ingest_status: dict[str, object] = {
    "status": "idle",
    "progress": 0,
    "message": None,
    "warnings": [],
    "error": None,
}


class IngestHistoryRequest(BaseModel):
    repo_path: str | None = None
    branch: str | None = None
    commit: str | None = None
    max_commits: int = 500
    include_pr_comments: bool = True
    allow_external_llm_for_private_repo: bool = False


@router.post("/ingest/history", status_code=202)
def post_ingest_history(request: IngestHistoryRequest | None = None) -> dict[str, object]:
    settings = get_settings()
    request = request or IngestHistoryRequest(max_commits=settings.max_commits_ingest)
    if not settings.devonboard_graph_path.exists():
        message = "No graph found. Run scan before ingesting history."
        _ingest_status.update({"status": "error", "progress": 0, "error": message})
        raise HTTPException(status_code=404, detail=message)

    _ingest_status.update(
        {"status": "running", "progress": 10, "message": "Ingesting history", "error": None}
    )
    try:
        store = GraphStore.load(settings.devonboard_graph_path)
        resolved = resolve_repository_input(
            request.repo_path or store.graph.repo.url or store.graph.repo.path or settings.target_repo_path,
            branch=request.branch or store.graph.repo.branch or settings.target_repo_branch,
            commit=request.commit or store.graph.repo.commit,
            cache_root=settings.repo_cache_path,
        )
        graph = GitHistoryIngestor(
            repo_path=resolved.path,
            graph=store.graph,
            max_commits=request.max_commits,
        ).ingest()
        graph.repo.path = str(resolved.path)
        graph.repo.url = resolved.url or graph.repo.url
        graph.repo.branch = resolved.branch
        graph.repo.commit = resolved.commit
        store.graph = graph
        store.save()
    except (subprocess.CalledProcessError, ValueError) as exc:
        message = f"Git history ingest failed: {exc}"
        _ingest_status.update({"status": "error", "progress": 0, "error": message})
        raise HTTPException(status_code=422, detail=message) from exc

    _ingest_status.update(
        {
            "status": "done",
            "progress": 100,
            "message": f"Ingested up to {request.max_commits} commits.",
            "warnings": [],
            "error": None,
            "resolved_repo_path": str(resolved.path),
            "repo_url": resolved.url,
            "repo_name": resolved.name,
        }
    )
    return _ingest_status


@router.get("/ingest/history/status")
def get_ingest_history_status() -> dict[str, object]:
    return _ingest_status
