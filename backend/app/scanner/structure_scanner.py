import fnmatch
import re
from pathlib import Path

from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import edge_id, file_id, function_id, module_id, normalize_repo_path
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta

GO_FUNCTION_RE = re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
GO_IMPORT_RE = re.compile(r'import\s+(?:\((?P<block>.*?)\)|"(?P<single>[^"]+)")', re.DOTALL)
GO_IMPORT_PATH_RE = re.compile(r'"([^"]+)"')
GO_TYPE_RE = re.compile(r"^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+", re.MULTILINE)

PYTHON_FUNCTION_RE = re.compile(r"^[ \t]*def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
PYTHON_CLASS_RE = re.compile(r"^[ \t]*class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*[:\(]", re.MULTILINE)
PYTHON_FROM_IMPORT_RE = re.compile(r"^[ \t]*from\s+(?P<module>[A-Za-z0-9_\.]+)\s+import\s+(?P<names>[A-Za-z0-9_,\*\s\(\)]+)", re.MULTILINE)
PYTHON_IMPORT_RE = re.compile(r"^[ \t]*import\s+(?P<module>[A-Za-z0-9_\.,\s]+)", re.MULTILINE)

TSJS_FUNCTION_RE = re.compile(
    r"^[ \t]*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(|"
    r"^[ \t]*(?:export\s+)?(?:const|let|var)\s+(?P<arrow_name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    re.MULTILINE
)
TSJS_CLASS_RE = re.compile(
    r"^[ \t]*(?:export\s+(?:default\s+)?)?class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*",
    re.MULTILINE
)
TSJS_IMPORT_RE = re.compile(r"^[ \t]*import\s+(?:.*\s+from\s+)?['\"](?P<path>[^'\"]+)['\"]", re.MULTILINE)


class StructureScanner:
    def __init__(
        self,
        repo_path: Path,
        branch: str,
        commit: str | None,
        exclude_patterns: list[str],
        repo_url: str | None = None,
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.branch = branch
        self.commit = commit
        self.exclude_patterns = exclude_patterns
        self.repo_url = repo_url
        self.go_module = self._read_go_module()

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
                url=self.repo_url,
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
            self._add_go_import_edges(store, relative, text, file_node.id)
        elif relative.endswith((".py", ".pyw")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            self._add_python_symbols(store, relative, text, file_node.id)
            self._add_python_import_edges(store, relative, text, file_node.id)
        elif relative.endswith((".ts", ".tsx", ".js", ".jsx")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            self._add_tsjs_symbols(store, relative, text, file_node.id)
            self._add_tsjs_import_edges(store, relative, text, file_node.id)

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

    def _add_python_symbols(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        for match in PYTHON_FUNCTION_RE.finditer(text):
            name = match.group("name")
            node = GraphNode(
                id=function_id(relative, name),
                type="function",
                name=name,
                summary=f"Python function {name} in {relative}.",
                tags=["python", "function"],
                filePath=relative,
                metadata={"language": "python"},
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

        for match in PYTHON_CLASS_RE.finditer(text):
            name = match.group("name")
            node = GraphNode(
                id=f"class:{relative}:{name}",
                type="class",
                name=name,
                summary=f"Python class {name} in {relative}.",
                tags=["python", "class"],
                filePath=relative,
                metadata={"language": "python"},
            )
            store.upsert_node(node)
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(file_node_id, node.id, "contains"),
                    source=file_node_id,
                    target=node.id,
                    type="contains",
                    summary="File contains class.",
                    weight=1.0,
                )
            )

    def _add_python_import_edges(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        imported_modules = set()
        for match in PYTHON_FROM_IMPORT_RE.finditer(text):
            mod = match.group("module")
            if mod:
                imported_modules.add(mod)
        for match in PYTHON_IMPORT_RE.finditer(text):
            mods = match.group("module")
            if mods:
                for mod in re.split(r",\s*", mods):
                    imported_modules.add(mod.strip())

        for mod in imported_modules:
            if mod.startswith("."):
                dot_count = 0
                for char in mod:
                    if char == ".":
                        dot_count += 1
                    else:
                        break
                remaining = mod[dot_count:]
                remaining_parts = remaining.split(".") if remaining else []
                curr_parent = Path(relative).parent
                target_dir = curr_parent
                for _ in range(dot_count - 1):
                    target_dir = target_dir.parent
                candidate_paths = [
                    (target_dir / Path(*remaining_parts)).with_suffix(".py"),
                    (target_dir / Path(*remaining_parts)) / "__init__.py"
                ]
            else:
                mod_parts = mod.split(".")
                candidate_paths = [
                    Path(*mod_parts).with_suffix(".py"),
                    Path(*mod_parts) / "__init__.py"
                ]

            resolved_rel = None
            for p in candidate_paths:
                try:
                    full_p = (self.repo_path / p).resolve()
                    if full_p.is_file() and full_p.is_relative_to(self.repo_path):
                        resolved_rel = normalize_repo_path(str(full_p.relative_to(self.repo_path)))
                        break
                except Exception:
                    pass

            if resolved_rel:
                target_id = file_id(resolved_rel)
                if not any(n.id == target_id for n in store.graph.nodes):
                    store.upsert_node(
                        GraphNode(
                            id=target_id,
                            type="file",
                            name=Path(resolved_rel).name,
                            summary=self._file_summary(resolved_rel),
                            tags=self._file_tags(resolved_rel),
                            filePath=resolved_rel,
                            metadata={"language": self._language_for(resolved_rel)},
                        )
                    )
                store.upsert_edge(
                    GraphEdge(
                        id=edge_id(file_node_id, target_id, "imports"),
                        source=file_node_id,
                        target=target_id,
                        type="imports",
                        summary=f"Python file imports {mod}.",
                        weight=0.7,
                        metadata={"importPath": mod},
                    )
                )

    def _add_tsjs_symbols(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        for match in TSJS_FUNCTION_RE.finditer(text):
            name = match.group("name") or match.group("arrow_name")
            if not name:
                continue
            node = GraphNode(
                id=function_id(relative, name),
                type="function",
                name=name,
                summary=f"JavaScript/TypeScript function {name} in {relative}.",
                tags=["javascript", "typescript", "function"],
                filePath=relative,
                metadata={"language": self._language_for(relative)},
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

        for match in TSJS_CLASS_RE.finditer(text):
            name = match.group("name")
            node = GraphNode(
                id=f"class:{relative}:{name}",
                type="class",
                name=name,
                summary=f"JavaScript/TypeScript class {name} in {relative}.",
                tags=["javascript", "typescript", "class"],
                filePath=relative,
                metadata={"language": self._language_for(relative)},
            )
            store.upsert_node(node)
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(file_node_id, node.id, "contains"),
                    source=file_node_id,
                    target=node.id,
                    type="contains",
                    summary="File contains class.",
                    weight=1.0,
                )
            )

    def _add_tsjs_import_edges(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        imported_paths = set()
        for match in TSJS_IMPORT_RE.finditer(text):
            p = match.group("path")
            if p:
                imported_paths.add(p)

        curr_parent = Path(relative).parent
        for imp_path in imported_paths:
            resolved_rel = None
            if imp_path.startswith("@/"):
                if relative.startswith("frontend/"):
                    suffix_path = imp_path.removeprefix("@/")
                    for prefix in ["frontend", "frontend/src"]:
                        candidate_paths = [
                            Path(prefix) / suffix_path,
                            Path(prefix) / (suffix_path + ".ts"),
                            Path(prefix) / (suffix_path + ".tsx"),
                            Path(prefix) / (suffix_path + ".js"),
                            Path(prefix) / (suffix_path + ".jsx"),
                            Path(prefix) / suffix_path / "index.ts",
                            Path(prefix) / suffix_path / "index.tsx",
                        ]
                        for cp in candidate_paths:
                            try:
                                full_p = (self.repo_path / cp).resolve()
                                if full_p.is_file() and full_p.is_relative_to(self.repo_path):
                                    resolved_rel = normalize_repo_path(str(full_p.relative_to(self.repo_path)))
                                    break
                            except Exception:
                                pass
                        if resolved_rel:
                            break
            elif imp_path.startswith((".", "..")):
                suffix_path = imp_path
                candidate_paths = [
                    curr_parent / suffix_path,
                    curr_parent / (suffix_path + ".ts"),
                    curr_parent / (suffix_path + ".tsx"),
                    curr_parent / (suffix_path + ".js"),
                    curr_parent / (suffix_path + ".jsx"),
                    curr_parent / suffix_path / "index.ts",
                    curr_parent / suffix_path / "index.tsx",
                ]
                for cp in candidate_paths:
                    try:
                        full_p = (self.repo_path / cp).resolve()
                        if full_p.is_file() and full_p.is_relative_to(self.repo_path):
                            resolved_rel = normalize_repo_path(str(full_p.relative_to(self.repo_path)))
                            break
                    except Exception:
                        pass

            if resolved_rel:
                target_id = file_id(resolved_rel)
                if not any(n.id == target_id for n in store.graph.nodes):
                    store.upsert_node(
                        GraphNode(
                            id=target_id,
                            type="file",
                            name=Path(resolved_rel).name,
                            summary=self._file_summary(resolved_rel),
                            tags=self._file_tags(resolved_rel),
                            filePath=resolved_rel,
                            metadata={"language": self._language_for(resolved_rel)},
                        )
                    )
                store.upsert_edge(
                    GraphEdge(
                        id=edge_id(file_node_id, target_id, "imports"),
                        source=file_node_id,
                        target=target_id,
                        type="imports",
                        summary=f"TS/JS file imports {imp_path}.",
                        weight=0.7,
                        metadata={"importPath": imp_path},
                    )
                )

    def _file_summary(self, relative: str) -> str:
        if relative.endswith(".go"):
            return f"Go source file {relative}."
        if relative.endswith((".py", ".pyw")):
            return f"Python source file {relative}."
        if relative.endswith((".ts", ".tsx")):
            return f"TypeScript source file {relative}."
        if relative.endswith((".js", ".jsx")):
            return f"JavaScript source file {relative}."
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

    def _read_go_module(self) -> str | None:
        go_mod = self.repo_path / "go.mod"
        if not go_mod.exists():
            return None
        for line in go_mod.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("module "):
                return line.split(None, 1)[1].strip()
        return None

    def _add_go_import_edges(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        if not self.go_module:
            return
        imports: list[str] = []
        for match in GO_IMPORT_RE.finditer(text):
            if match.group("single"):
                imports.append(match.group("single"))
            else:
                imports.extend(GO_IMPORT_PATH_RE.findall(match.group("block") or ""))
        for import_path in sorted(set(imports)):
            if not import_path.startswith(f"{self.go_module}/"):
                continue
            module_path = normalize_repo_path(import_path.removeprefix(f"{self.go_module}/"))
            target_id = module_id(module_path)
            store.upsert_node(
                GraphNode(
                    id=target_id,
                    type="module",
                    name=Path(module_path).name,
                    summary=f"Module imported from {module_path}.",
                    tags=["module", "imported"],
                    filePath=module_path,
                )
            )
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(file_node_id, target_id, "imports"),
                    source=file_node_id,
                    target=target_id,
                    type="imports",
                    summary=f"File imports {import_path}.",
                    weight=0.7,
                    metadata={"importPath": import_path},
                )
            )
