from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.services.benchmark import BenchmarkService

router = APIRouter()


class BenchmarkRequest(BaseModel):
    repo: str = "demo"
    target_branch: str = "dev"
    target_commit: str | None = None


@router.post("/benchmark", status_code=202)
def post_benchmark(request: BenchmarkRequest | None = None) -> dict[str, str]:
    request = request or BenchmarkRequest()
    settings = get_settings()
    if not settings.devonboard_graph_path.exists():
        raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
    graph = GraphStore.load(settings.devonboard_graph_path).graph
    run = BenchmarkService(graph).run(
        repo=request.repo,
        target_branch=request.target_branch,
        target_commit=request.target_commit,
    )
    return {"run_id": str(run["run_id"]), "status": "running"}


@router.get("/benchmark/results")
def get_benchmark_results() -> list[dict[str, object]]:
    return BenchmarkService(GraphStore.load(get_settings().devonboard_graph_path).graph).list_runs()


@router.get("/benchmark/results/{run_id}")
def get_benchmark_run(run_id: str) -> dict[str, object]:
    run = BenchmarkService(GraphStore.load(get_settings().devonboard_graph_path).graph).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Benchmark run not found: {run_id}")
    return run
