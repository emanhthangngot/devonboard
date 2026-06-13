from pathlib import Path

from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import claim_id, edge_id, file_id, function_id, source_commit_id
from backend.app.graph.models import GraphEdge, GraphNode, RepoMeta


def test_deterministic_graph_ids_are_stable() -> None:
    assert file_id("internal/agent/pipeline.go") == "file:internal/agent/pipeline.go"
    assert function_id("internal/agent/pipeline.go", "ExecutePipeline") == (
        "function:internal/agent/pipeline.go:ExecutePipeline"
    )
    assert source_commit_id("a3f2b1c9d4e5") == "source:commit:a3f2b1c9d4e5"
    assert claim_id("Pipeline stages should be independently testable") == (
        "claim:pipeline-stages-should-be-independently-testable"
    )
    assert edge_id("file:a", "source:commit:1", "documents") == (
        "edge:documents:file:a->source:commit:1"
    )


def test_store_upserts_nodes_and_edges_without_duplicates(tmp_path: Path) -> None:
    store = GraphStore(
        path=tmp_path / "devonboard" / "knowledge-graph.json",
        repo=RepoMeta(name="demo", path="/tmp/demo", branch="dev", commit="abc123"),
    )

    node = GraphNode(
        id=file_id("internal/agent/pipeline.go"),
        type="file",
        name="pipeline.go",
        summary="Pipeline implementation.",
        tags=["pipeline"],
        filePath="internal/agent/pipeline.go",
        metadata={"language": "go"},
    )
    updated = node.model_copy(
        update={
            "summary": "Pipeline implementation and tool execution.",
            "tags": ["tool", "pipeline"],
            "metadata": {"owner": "agent"},
        }
    )

    source = GraphNode(
        id=source_commit_id("abc123"),
        type="source",
        name="refactor pipeline",
        summary="Split pipeline into stages.",
        tags=["git", "commit"],
    )
    edge = GraphEdge(
        id=edge_id(node.id, source.id, "documents"),
        source=node.id,
        target=source.id,
        type="documents",
        summary="Commit documents the pipeline file.",
        weight=1.0,
    )

    store.upsert_node(node)
    store.upsert_node(updated)
    store.upsert_node(source)
    store.upsert_edge(edge)
    store.upsert_edge(edge)

    graph = store.graph
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    pipeline = graph.node_by_id(node.id)
    assert pipeline.summary == "Pipeline implementation and tool execution."
    assert pipeline.tags == ["pipeline", "tool"]
    assert pipeline.metadata == {"language": "go", "owner": "agent"}


def test_store_persists_and_loads_graph_json(tmp_path: Path) -> None:
    graph_path = tmp_path / "devonboard" / "knowledge-graph.json"
    store = GraphStore(
        path=graph_path,
        repo=RepoMeta(name="demo", path="/tmp/demo", branch="dev", commit=None),
    )
    store.upsert_node(
        GraphNode(
            id=file_id("README.md"),
            type="file",
            name="README.md",
            summary="Repository overview.",
            tags=[],
            filePath="README.md",
        )
    )
    store.save()

    loaded = GraphStore.load(graph_path)

    assert graph_path.exists()
    assert loaded.graph.version == "0.1.0"
    assert loaded.graph.repo.name == "demo"
    assert loaded.graph.node_by_id(file_id("README.md")).name == "README.md"
