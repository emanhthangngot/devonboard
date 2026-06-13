from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import file_id
from backend.app.graph.models import RepoMeta
from backend.app.main import health
from backend.app.scanner.structure_scanner import StructureScanner


def main() -> None:
    payload = health()
    if payload.get("status") != "ok":
        raise SystemExit(f"health status was not ok: {payload}")
    print("backend smoke: /health ok")

    with TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        repo.mkdir()
        (repo / "main.go").write_text("package main\n\nfunc main() {}\n", encoding="utf-8")
        graph = StructureScanner(repo, branch="dev", commit="smoke", exclude_patterns=[]).scan()
        graph_path = Path(temp_dir) / "devonboard" / "knowledge-graph.json"
        GraphStore(
            path=graph_path,
            repo=RepoMeta(name="repo", path=str(repo), branch="dev", commit="smoke"),
            graph=graph,
        ).save()
        loaded = GraphStore.load(graph_path)
        loaded.graph.node_by_id(file_id("main.go"))
        print("backend smoke: scan graph ok")


if __name__ == "__main__":
    main()
