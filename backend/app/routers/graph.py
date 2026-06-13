from fastapi import APIRouter, HTTPException

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.services.retrieval import RetrievalService

router = APIRouter()


@router.get("/graph")
def get_graph() -> dict[str, object]:
    settings = get_settings()
    if not settings.devonboard_graph_path.exists():
        raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
    return GraphStore.load(settings.devonboard_graph_path).graph.model_dump(by_alias=True)


@router.get("/graph/node/{node_id:path}/history")
def get_graph_node_history(node_id: str) -> dict[str, object]:
    settings = get_settings()
    if not settings.devonboard_graph_path.exists():
        raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
    graph = GraphStore.load(settings.devonboard_graph_path).graph
    if not any(node.id == node_id for node in graph.nodes):
        raise HTTPException(status_code=404, detail=f"Graph node not found: {node_id}")
    return RetrievalService(graph).node_history(node_id)
