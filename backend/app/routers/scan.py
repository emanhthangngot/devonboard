from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.scanner.structure_scanner import StructureScanner
from backend.app.services.repo_resolver import resolve_repository_input

router = APIRouter()

_scan_status: dict[str, object] = {
    "status": "idle",
    "progress": 0,
    "message": None,
    "warnings": [],
    "error": None,
}


class ScanRequest(BaseModel):
    repo_path: str
    branch: str = "dev"
    commit: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)


@router.post("/scan", status_code=202)
def post_scan(request: ScanRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
    _scan_status.update({"status": "running", "progress": 0, "message": "Queued", "error": None})
    background_tasks.add_task(_run_scan, request)
    return _scan_status


def _run_scan(request: ScanRequest) -> None:
    from backend.app.main import set_cached_graph, invalidate_graph_cache
    invalidate_graph_cache()
    settings = get_settings()
    exclude_patterns = request.exclude_patterns or [
        p.strip() for p in settings.exclude_patterns.split(",") if p.strip()
    ]
    _scan_status.update({"status": "running", "progress": 10, "message": "Scanning"})
    try:
        resolved = resolve_repository_input(
            request.repo_path,
            branch=request.branch,
            commit=request.commit,
            cache_root=settings.repo_cache_path,
        )
        graph = StructureScanner(
            repo_path=resolved.path,
            branch=request.branch,
            commit=request.commit,
            exclude_patterns=exclude_patterns,
            repo_url=resolved.url,
        ).scan()
        store = GraphStore(path=settings.devonboard_graph_path, repo=graph.repo, graph=graph)
        store.save()
        set_cached_graph(graph)
        _scan_status.update({
            "status": "done",
            "progress": 100,
            "message": f"Scanned {len(graph.nodes)} nodes and {len(graph.edges)} edges.",
            "warnings": [],
            "error": None,
            "resolved_repo_path": str(resolved.path),
            "repo_url": resolved.url,
            "repo_name": resolved.name,
        })
    except Exception as exc:
        _scan_status.update({"status": "error", "progress": 0, "error": str(exc)})



@router.get("/scan/status")
def get_scan_status() -> dict[str, object]:
    return _scan_status
