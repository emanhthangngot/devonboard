from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, Query

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.services.retrieval import RetrievalService

router = APIRouter()



@router.get("/graph")
def get_graph() -> dict[str, object]:
    from backend.app.main import get_cached_graph, set_cached_graph
    settings = get_settings()
    graph = get_cached_graph()
    if graph is None:
        if not settings.devonboard_graph_path.exists():
            raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
        graph = GraphStore.load(settings.devonboard_graph_path).graph
        set_cached_graph(graph)
    return graph.model_dump(by_alias=True)


@router.get("/graph/summary")
def get_graph_summary() -> dict[str, object]:
    graph = _load_graph()
    node_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}
    for node in graph.nodes:
        node_counts[node.type] = node_counts.get(node.type, 0) + 1
    for edge in graph.edges:
        edge_counts[edge.type] = edge_counts.get(edge.type, 0) + 1
    return {
        "version": graph.version,
        "generated_at": graph.generated_at.isoformat(),
        "repo": graph.repo.model_dump(),
        "node_counts": node_counts,
        "edge_counts": edge_counts,
        "total_nodes": len(graph.nodes),
        "total_edges": len(graph.edges),
    }


@router.get("/graph/nodes")
def get_graph_nodes(
    type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: int = Query(default=0, ge=0),
) -> dict[str, object]:
    graph = _load_graph()
    term = (q or "").strip().lower()
    nodes = graph.nodes
    if type:
        allowed = {item.strip() for item in type.split(",") if item.strip()}
        nodes = [node for node in nodes if node.type in allowed]
    if term:
        nodes = [
            node
            for node in nodes
            if term in " ".join([node.id, node.name, node.summary, *node.tags]).lower()
        ]
    page = nodes[cursor : cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(nodes) else None
    return {
        "nodes": [node.model_dump(by_alias=True) for node in page],
        "next_cursor": next_cursor,
        "total": len(nodes),
    }


@router.get("/graph/node/{node_id:path}/history")
def get_graph_node_history(node_id: str) -> dict[str, object]:
    node_id = unquote(node_id)
    graph = _load_graph()
    if not any(node.id == node_id for node in graph.nodes):
        raise HTTPException(status_code=404, detail=f"Graph node not found: {node_id}")
    return RetrievalService(graph).node_history(node_id)


def _load_graph():
    from backend.app.main import get_cached_graph, set_cached_graph

    settings = get_settings()
    graph = get_cached_graph()
    if graph is None:
        if not settings.devonboard_graph_path.exists():
            raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
        graph = GraphStore.load(settings.devonboard_graph_path).graph
        set_cached_graph(graph)
    return graph
