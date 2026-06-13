from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.scanner.structure_scanner import StructureScanner

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
def post_scan(request: ScanRequest) -> dict[str, object]:
    settings = get_settings()
    exclude_patterns = request.exclude_patterns or [
        pattern.strip()
        for pattern in settings.exclude_patterns.split(",")
        if pattern.strip()
    ]
    _scan_status.update({"status": "running", "progress": 10, "message": "Scanning", "error": None})
    try:
        graph = StructureScanner(
            repo_path=Path(request.repo_path),
            branch=request.branch,
            commit=request.commit,
            exclude_patterns=exclude_patterns,
        ).scan()
        store = GraphStore(path=settings.devonboard_graph_path, repo=graph.repo, graph=graph)
        store.save()
    except FileNotFoundError as exc:
        _scan_status.update({"status": "error", "progress": 0, "error": str(exc)})
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _scan_status.update(
        {
            "status": "done",
            "progress": 100,
            "message": f"Scanned {len(graph.nodes)} nodes and {len(graph.edges)} edges.",
            "warnings": [],
            "error": None,
        }
    )
    return _scan_status


@router.get("/scan/status")
def get_scan_status() -> dict[str, object]:
    return _scan_status
