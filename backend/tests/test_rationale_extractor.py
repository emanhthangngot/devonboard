from backend.app.graph.ids import source_commit_id
from backend.app.graph.models import GraphNode, KnowledgeGraph, RepoMeta
from backend.app.ingest.rationale_extractor import RationaleExtractor


def source_node(summary: str) -> GraphNode:
    return GraphNode(
        id=source_commit_id("abc123"),
        type="source",
        name="refactor: split pipeline",
        summary=summary,
        tags=["git", "commit"],
        metadata={"kind": "commit"},
    )


def test_rationale_extractor_creates_claim_from_explicit_evidence() -> None:
    graph = KnowledgeGraph(
        repo=RepoMeta(name="demo", path="/tmp/demo"),
        nodes=[
            source_node(
                "Split the pipeline because each stage needs to be independently testable."
            )
        ],
    )

    extracted = RationaleExtractor(graph).extract()

    claims = [node for node in extracted.nodes if node.type == "claim"]
    assert len(claims) == 1
    assert claims[0].metadata["extractedFrom"] == [source_commit_id("abc123")]
    assert claims[0].metadata["confidence"] >= 0.6
    assert "testable" in claims[0].summary
    assert any(edge.type == "exemplifies" and edge.target == claims[0].id for edge in extracted.edges)


def test_rationale_extractor_discards_sources_without_explicit_rationale() -> None:
    graph = KnowledgeGraph(
        repo=RepoMeta(name="demo", path="/tmp/demo"),
        nodes=[source_node("Update files and adjust formatting.")],
    )

    extracted = RationaleExtractor(graph).extract()

    assert [node for node in extracted.nodes if node.type == "claim"] == []
