from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.services.evidence_pack import EvidencePackService

router = APIRouter()


class EvidencePackRequest(BaseModel):
    purpose: str
    query: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    allow_external_llm_for_private_repo: bool = False


@router.post("/evidence-packs")
def post_evidence_pack(request: EvidencePackRequest) -> dict[str, object]:
    from backend.app.main import get_cached_graph, set_cached_graph
    settings = get_settings()
    if request.purpose not in {"pr_review", "ai_agent_context"}:
        raise HTTPException(status_code=422, detail="purpose must be pr_review or ai_agent_context")
    graph = get_cached_graph()
    if graph is None:
        if not settings.devonboard_graph_path.exists():
            raise HTTPException(status_code=404, detail="No graph found. Run scan to get started.")
        graph = GraphStore.load(settings.devonboard_graph_path).graph
        set_cached_graph(graph)
    return EvidencePackService(graph).create(
        purpose=request.purpose,  # type: ignore[arg-type]
        query=request.query,
        node_ids=request.node_ids,
        changed_files=request.changed_files,
        allow_external_llm_for_private_repo=request.allow_external_llm_for_private_repo,
    )

