from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import file_id
from backend.app.graph.models import RepoMeta
from backend.app.ingest.git_extractor import GitHistoryIngestor
from backend.app.main import health
from backend.app.scanner.structure_scanner import StructureScanner
from backend.app.services.benchmark import BenchmarkService
from backend.app.services.evidence_pack import EvidencePackService
from backend.app.services.retrieval import RetrievalService


def main() -> None:
    payload = health()
    if payload.get("status") != "ok":
        raise SystemExit(f"health status was not ok: {payload}")
    print("backend smoke: /health ok")

    with TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        repo.mkdir()
        subprocess.check_call(["git", "-C", str(repo), "init", "-b", "dev"], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["git", "-C", str(repo), "config", "user.email", "smoke@example.com"],
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["git", "-C", str(repo), "config", "user.name", "Smoke Test"],
            stdout=subprocess.DEVNULL,
        )
        (repo / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
        subprocess.check_call(["git", "-C", str(repo), "add", "main.go"], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["git", "-C", str(repo), "commit", "-m", "feat: add smoke main"],
            stdout=subprocess.DEVNULL,
        )
        graph = StructureScanner(repo, branch="dev", commit="smoke", exclude_patterns=[]).scan()
        graph = GitHistoryIngestor(repo_path=repo, graph=graph, max_commits=5).ingest()
        graph_path = Path(temp_dir) / "devonboard" / "knowledge-graph.json"
        GraphStore(
            path=graph_path,
            repo=RepoMeta(name="repo", path=str(repo), branch="dev", commit="smoke"),
            graph=graph,
        ).save()
        loaded = GraphStore.load(graph_path)
        loaded.graph.node_by_id(file_id("main.go"))
        if not any(node.type == "source" for node in loaded.graph.nodes):
            raise SystemExit("history ingest did not create source nodes")
        result = RetrievalService(loaded.graph).answer(
            "Is it safe to refactor main?", mode="auto", node_ids=[]
        )
        if not result.citations:
            raise SystemExit("query did not return citations")
        pack = EvidencePackService(loaded.graph).create(
            purpose="pr_review",
            query="Review main",
            changed_files=["main.go"],
        )
        if not pack["citations"]:
            raise SystemExit("evidence pack did not return citations")
        run = BenchmarkService(
            loaded.graph,
            results_dir=Path(temp_dir) / "benchmark" / "results",
        ).run(repo="repo", target_branch="dev", target_commit="smoke")
        if len(run["rows"]) != 10:
            raise SystemExit("benchmark did not create fixed query comparison rows")
        print("backend smoke: scan graph ok")
        print("backend smoke: history ingest ok")
        print("backend smoke: cited query ok")
        print("backend smoke: evidence pack ok")
        print("backend smoke: benchmark ok")


if __name__ == "__main__":
    main()
