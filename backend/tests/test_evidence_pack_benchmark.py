from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import edge_id, file_id, source_commit_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta
from backend.app.main import app


def write_pack_graph(path: Path) -> None:
    file_node = GraphNode(
        id=file_id("internal/providers/adapter.go"),
        type="file",
        name="adapter.go",
        summary="Provider adapter implementation.",
        tags=["provider", "adapter"],
        filePath="internal/providers/adapter.go",
    )
    source_node = GraphNode(
        id=source_commit_id("abc123"),
        type="source",
        name="fix: stabilize provider adapter",
        summary="Stabilized ProviderAdapter because provider integrations were fragile.",
        tags=["git", "commit", "provider"],
        metadata={"kind": "commit", "hash": "abc123", "filesTouched": ["internal/providers/adapter.go"]},
    )
    graph = KnowledgeGraph(
        repo=RepoMeta(name="demo", path="/tmp/demo", branch="dev"),
        nodes=[file_node, source_node],
        edges=[
            GraphEdge(
                id=edge_id(source_node.id, file_node.id, "documents"),
                source=source_node.id,
                target=file_node.id,
                type="documents",
                weight=1.0,
            )
        ],
    )
    GraphStore(path=path, repo=graph.repo, graph=graph).save()


def test_evidence_pack_api_returns_markdown_and_citations(tmp_path: Path) -> None:
    graph_path = tmp_path / "knowledge-graph.json"
    write_pack_graph(graph_path)
    settings = get_settings()
    original = settings.devonboard_graph_path
    settings.devonboard_graph_path = graph_path
    try:
        response = TestClient(app).post(
            "/evidence-packs",
            json={
                "purpose": "pr_review",
                "changed_files": ["internal/providers/adapter.go"],
                "query": "ProviderAdapter review",
            },
        )
    finally:
        settings.devonboard_graph_path = original

    assert response.status_code == 200
    payload = response.json()
    assert payload["purpose"] == "pr_review"
    assert "Changed scope" in payload["markdown"]
    assert payload["citations"]


def test_benchmark_api_persists_fixed_query_run(tmp_path: Path, monkeypatch) -> None:
    graph_path = tmp_path / "knowledge-graph.json"
    results_dir = tmp_path / "benchmark" / "results"
    write_pack_graph(graph_path)
    monkeypatch.setenv("DEVONBOARD_BENCHMARK_RESULTS_DIR", str(results_dir))
    settings = get_settings()
    original = settings.devonboard_graph_path
    settings.devonboard_graph_path = graph_path
    try:
        client = TestClient(app)
        started = client.post("/benchmark", json={"repo": "demo", "target_branch": "dev"})
        listed = client.get("/benchmark/results")
    finally:
        settings.devonboard_graph_path = original

    assert started.status_code == 202
    run_id = started.json()["run_id"]
    assert listed.status_code == 200
    assert listed.json()[0]["run_id"] == run_id
    assert (results_dir / f"{run_id}.json").exists()
