import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.services.retrieval import RetrievalService

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: str = "auto"
    node_ids: list[str] = Field(default_factory=list)
    allow_external_llm_for_private_repo: bool = False


@router.post("/query")
def post_query(request: QueryRequest) -> dict[str, object]:
    graph = _load_graph()
    return RetrievalService(graph).answer(
        query=request.query,
        mode=request.mode,
        node_ids=request.node_ids,
        allow_external_llm=request.allow_external_llm_for_private_repo,
    ).as_dict()


@router.post("/query/stream")
def post_query_stream(request: QueryRequest) -> StreamingResponse:
    graph = _load_graph()
    service = RetrievalService(graph)

    def events():
        for event in service.answer_stream(
            query=request.query,
            mode=request.mode,
            node_ids=request.node_ids,
            allow_external_llm=request.allow_external_llm_for_private_repo,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


def _load_graph():
    from backend.app.main import get_cached_graph, set_cached_graph
    graph = get_cached_graph()
    if graph is None:
        settings = get_settings()
        if not settings.devonboard_graph_path.exists():
            raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
        graph = GraphStore.load(settings.devonboard_graph_path).graph
        set_cached_graph(graph)
    return graph

