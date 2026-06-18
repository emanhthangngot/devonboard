from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.models import KnowledgeGraph, RepoMeta
from backend.app.services.results import ResultService

router = APIRouter()


class ResultRequest(BaseModel):
    repo: str = "demo"
    target_branch: str = "dev"
    target_commit: str | None = None


@router.post("/results", status_code=202)
def post_results(request: ResultRequest | None = None) -> dict[str, str]:
    from backend.app.main import get_cached_graph, set_cached_graph
    request = request or ResultRequest()
    settings = get_settings()
    graph = get_cached_graph()
    if graph is None:
        if not settings.devonboard_graph_path.exists():
            raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
        graph = GraphStore.load(settings.devonboard_graph_path).graph
        set_cached_graph(graph)
    run = ResultService(graph, results_dir=settings.results_dir).run(
        repo=request.repo,
        target_branch=request.target_branch,
        target_commit=request.target_commit,
    )
    return {"run_id": str(run["run_id"]), "status": "running"}


@router.get("/results/runs")
def get_result_runs() -> list[dict[str, object]]:
    empty_graph = KnowledgeGraph(repo=RepoMeta(name="demo", path="."))
    return ResultService(empty_graph, results_dir=get_settings().results_dir).list_runs()


@router.get("/results/runs/{run_id}")
def get_result_run(run_id: str) -> dict[str, object]:
    empty_graph = KnowledgeGraph(repo=RepoMeta(name="demo", path="."))
    run = ResultService(empty_graph, results_dir=get_settings().results_dir).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Result run not found: {run_id}")
    return run
