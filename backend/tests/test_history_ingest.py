import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import file_id
from backend.app.ingest.git_extractor import GitHistoryIngestor
from backend.app.main import app
from backend.app.scanner.structure_scanner import StructureScanner


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def create_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "-C", str(repo), "init", "-b", "dev"])
    git(repo, "config", "user.email", "devonboard@example.com")
    git(repo, "config", "user.name", "Dev Onboard")
    (repo / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
    git(repo, "add", "main.go")
    git(
        repo,
        "commit",
        "-m",
        "feat: add main entrypoint",
        "-m",
        "Split the entrypoint because startup behavior needs to stay testable.",
    )
    return repo


def test_git_history_ingest_links_commits_to_scanned_files(tmp_path: Path) -> None:
    repo = create_git_repo(tmp_path)
    graph = StructureScanner(repo, branch="dev", commit=None, exclude_patterns=[]).scan()

    ingested = GitHistoryIngestor(repo_path=repo, graph=graph, max_commits=10).ingest()

    commit_nodes = [node for node in ingested.nodes if node.type == "source"]
    entity_nodes = [node for node in ingested.nodes if node.type == "entity"]
    claim_nodes = [node for node in ingested.nodes if node.type == "claim"]
    assert len(commit_nodes) == 1
    assert len(claim_nodes) == 1
    assert commit_nodes[0].metadata["kind"] == "commit"
    assert commit_nodes[0].metadata["filesTouched"] == ["main.go"]
    assert entity_nodes[0].name == "Dev Onboard"

    edge_pairs = {(edge.source, edge.target, edge.type) for edge in ingested.edges}
    assert (commit_nodes[0].id, file_id("main.go"), "documents") in edge_pairs
    assert (commit_nodes[0].id, entity_nodes[0].id, "authored_by") in edge_pairs


def test_ingest_history_api_merges_into_existing_graph(tmp_path: Path) -> None:
    repo = create_git_repo(tmp_path)
    graph_path = tmp_path / "devonboard" / "knowledge-graph.json"
    graph = StructureScanner(repo, branch="dev", commit=None, exclude_patterns=[]).scan()
    GraphStore(path=graph_path, repo=graph.repo, graph=graph).save()

    settings = get_settings()
    original_repo_path = settings.target_repo_path
    original_graph_path = settings.devonboard_graph_path
    settings.target_repo_path = repo
    settings.devonboard_graph_path = graph_path
    try:
        response = TestClient(app).post("/ingest/history", json={"max_commits": 5})
    finally:
        settings.target_repo_path = original_repo_path
        settings.devonboard_graph_path = original_graph_path

    assert response.status_code == 202
    assert response.json()["status"] == "done"
    loaded = GraphStore.load(graph_path)
    assert any(node.type == "source" for node in loaded.graph.nodes)
