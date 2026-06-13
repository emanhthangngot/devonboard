from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import edge_id, file_id, source_commit_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta
from backend.app.main import app


def write_graph(path: Path) -> None:
    file_node = GraphNode(
        id=file_id("internal/agent/pipeline.go"),
        type="file",
        name="pipeline.go",
        summary="Pipeline executes tool calls through staged handlers.",
        tags=["pipeline", "tool"],
        filePath="internal/agent/pipeline.go",
    )
    source_node = GraphNode(
        id=source_commit_id("abc123"),
        type="source",
        name="refactor: split pipeline",
        summary="Split the pipeline because each stage needs to be independently testable.",
        tags=["git", "commit", "pipeline"],
        metadata={"kind": "commit", "hash": "abc123", "filesTouched": ["internal/agent/pipeline.go"]},
    )
    claim_node = GraphNode(
        id="claim:pipeline-stages-testable",
        type="claim",
        name="Pipeline stages testable",
        summary="Each pipeline stage needs to be independently testable.",
        tags=["design-rationale", "testability"],
        metadata={"confidence": 0.72, "extractedFrom": [source_node.id]},
    )
    graph = KnowledgeGraph(
        repo=RepoMeta(name="demo", path="/tmp/demo", branch="dev"),
        nodes=[file_node, source_node, claim_node],
        edges=[
            GraphEdge(
                id=edge_id(source_node.id, file_node.id, "documents"),
                source=source_node.id,
                target=file_node.id,
                type="documents",
                weight=1.0,
            ),
            GraphEdge(
                id=edge_id(source_node.id, claim_node.id, "exemplifies"),
                source=source_node.id,
                target=claim_node.id,
                type="exemplifies",
                weight=0.8,
            ),
        ],
    )
    GraphStore(path=path, repo=graph.repo, graph=graph).save()


def with_graph(path: Path):
    settings = get_settings()
    original = settings.devonboard_graph_path
    settings.devonboard_graph_path = path
    return settings, original


def test_graph_and_node_history_endpoints_return_evidence(tmp_path: Path) -> None:
    graph_path = tmp_path / "knowledge-graph.json"
    write_graph(graph_path)
    settings, original = with_graph(graph_path)
    try:
        client = TestClient(app)
        graph_response = client.get("/graph")
        history_response = client.get(f"/graph/node/{file_id('internal/agent/pipeline.go')}/history")
    finally:
        settings.devonboard_graph_path = original

    assert graph_response.status_code == 200
    assert len(graph_response.json()["nodes"]) == 3
    assert history_response.status_code == 200
    assert history_response.json()["evidence"][0]["type"] == "commit"
    assert history_response.json()["claims"][0]["type"] == "claim"


def test_query_endpoint_returns_cited_hybrid_answer(tmp_path: Path) -> None:
    graph_path = tmp_path / "knowledge-graph.json"
    write_graph(graph_path)
    settings, original = with_graph(graph_path)
    try:
        response = TestClient(app).post(
            "/query",
            json={"query": "Is it safe to refactor the pipeline?", "mode": "auto"},
        )
    finally:
        settings.devonboard_graph_path = original

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "hybrid"
    assert payload["citations"]
    assert payload["structural"]
    assert payload["historical"]
    assert "Structural impact" in payload["answer"]
    assert "Historical context" in payload["answer"]
