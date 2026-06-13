import fnmatch
import re
from pathlib import Path

from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import edge_id, file_id, function_id, module_id, normalize_repo_path
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta

GO_FUNCTION_RE = re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
GO_TYPE_RE = re.compile(r"^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+", re.MULTILINE)


class StructureScanner:
    def __init__(
        self,
        repo_path: Path,
        branch: str,
        commit: str | None,
        exclude_patterns: list[str],
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.branch = branch
        self.commit = commit
        self.exclude_patterns = exclude_patterns

    def scan(self) -> KnowledgeGraph:
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")

        store = GraphStore(
            path=self.repo_path / "devonboard" / "knowledge-graph.json",
            repo=RepoMeta(
                name=self.repo_path.name,
                path=str(self.repo_path),
                branch=self.branch,
                commit=self.commit,
            ),
        )

        for path in sorted(self.repo_path.rglob("*")):
            if not path.is_file():
                continue
            relative = normalize_repo_path(str(path.relative_to(self.repo_path)))
            if self._is_excluded(relative):
                continue
            self._add_file(store, path, relative)

        return store.graph

    def _is_excluded(self, relative_path: str) -> bool:
        parts = relative_path.split("/")
        return any(
            fnmatch.fnmatch(relative_path, pattern)
            or any(fnmatch.fnmatch(part, pattern) for part in parts)
            for pattern in self.exclude_patterns
        )

    def _add_file(self, store: GraphStore, path: Path, relative: str) -> None:
        file_node = GraphNode(
            id=file_id(relative),
            type="file",
            name=Path(relative).name,
            summary=self._file_summary(relative),
            tags=self._file_tags(relative),
            filePath=relative,
            metadata={"language": self._language_for(relative)},
        )
        store.upsert_node(file_node)
        self._add_modules(store, relative, file_node.id)

        if relative.endswith(".go"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            self._add_go_symbols(store, relative, text, file_node.id)

    def _add_modules(self, store: GraphStore, relative: str, child_id: str) -> None:
        parent = Path(relative).parent
        if str(parent) == ".":
            return
        module_path = normalize_repo_path(str(parent))
        module_node = GraphNode(
            id=module_id(module_path),
            type="module",
            name=Path(module_path).name,
            summary=f"Module containing files under {module_path}.",
            tags=["module"],
            filePath=module_path,
        )
        store.upsert_node(module_node)
        store.upsert_edge(
            GraphEdge(
                id=edge_id(module_node.id, child_id, "contains"),
                source=module_node.id,
                target=child_id,
                type="contains",
                summary="Module contains file.",
                weight=1.0,
            )
        )

    def _add_go_symbols(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        for match in GO_FUNCTION_RE.finditer(text):
            name = match.group("name")
            node = GraphNode(
                id=function_id(relative, name),
                type="function",
                name=name,
                summary=f"Go function {name} in {relative}.",
                tags=["go", "function"],
                filePath=relative,
                metadata={"language": "go"},
            )
            store.upsert_node(node)
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(file_node_id, node.id, "contains"),
                    source=file_node_id,
                    target=node.id,
                    type="contains",
                    summary="File contains function.",
                    weight=1.0,
                )
            )

        for match in GO_TYPE_RE.finditer(text):
            name = match.group("name")
            node = GraphNode(
                id=f"class:{relative}:{name}",
                type="class",
                name=name,
                summary=f"Go type {name} in {relative}.",
                tags=["go", "type"],
                filePath=relative,
                metadata={"language": "go"},
            )
            store.upsert_node(node)
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(file_node_id, node.id, "contains"),
                    source=file_node_id,
                    target=node.id,
                    type="contains",
                    summary="File contains type.",
                    weight=1.0,
                )
            )

    def _file_summary(self, relative: str) -> str:
        if relative.endswith(".go"):
            return f"Go source file {relative}."
        if relative.lower().endswith((".md", ".txt")):
            return f"Documentation file {relative}."
        return f"Repository file {relative}; detailed symbols unavailable."

    def _file_tags(self, relative: str) -> list[str]:
        tags = ["file"]
        language = self._language_for(relative)
        if language:
            tags.append(language)
        return tags

    def _language_for(self, relative: str) -> str | None:
        suffix = Path(relative).suffix.lower()
        return {
            ".go": "go",
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }.get(suffix)
