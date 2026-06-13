from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.graph.ids import file_id, function_id, module_id
from backend.app.graph.graph_store import GraphStore
from backend.app.main import app
from backend.app.scanner.structure_scanner import StructureScanner


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_structure_scanner_builds_file_module_and_function_nodes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write_file(
        repo / "internal" / "agent" / "pipeline.go",
        """
package agent

import "context"

type Pipeline struct {}

func ExecutePipeline(ctx context.Context) error {
    return nil
}
""".strip(),
    )
    write_file(repo / "README.md", "# Demo\n")
    write_file(repo / "vendor" / "ignored.go", "package vendor\n")
    write_file(repo / ".env", "SECRET=value\n")

    graph = StructureScanner(
        repo_path=repo,
        branch="dev",
        commit="abc123",
        exclude_patterns=["vendor/**", ".env*"],
    ).scan()

    node_ids = {node.id for node in graph.nodes}
    assert file_id("internal/agent/pipeline.go") in node_ids
    assert module_id("internal/agent") in node_ids
    assert function_id("internal/agent/pipeline.go", "ExecutePipeline") in node_ids
    assert file_id("README.md") in node_ids
    assert file_id("vendor/ignored.go") not in node_ids
    assert file_id(".env") not in node_ids

    edge_pairs = {(edge.source, edge.target, edge.type) for edge in graph.edges}
    assert (module_id("internal/agent"), file_id("internal/agent/pipeline.go"), "contains") in edge_pairs
    assert (
        file_id("internal/agent/pipeline.go"),
        function_id("internal/agent/pipeline.go", "ExecutePipeline"),
        "contains",
    ) in edge_pairs


def test_scan_api_writes_graph_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    graph_path = tmp_path / "devonboard" / "knowledge-graph.json"
    write_file(repo / "main.go", "package main\n\nfunc main() {}\n")

    settings = get_settings()
    original_graph_path = settings.devonboard_graph_path
    settings.devonboard_graph_path = graph_path
    try:
        response = TestClient(app).post(
            "/scan",
            json={
                "repo_path": str(repo),
                "branch": "dev",
                "commit": "abc123",
                "exclude_patterns": [],
            },
        )
    finally:
        settings.devonboard_graph_path = original_graph_path

    assert response.status_code == 202
    assert response.json()["status"] == "done"
    loaded = GraphStore.load(graph_path)
    assert loaded.graph.node_by_id(file_id("main.go")).name == "main.go"
