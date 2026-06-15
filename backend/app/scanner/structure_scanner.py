import fnmatch
import re
from collections import defaultdict
from pathlib import Path

from backend.app.config import get_settings
from backend.app.graph.graph_store import GraphStore
from backend.app.graph.ids import edge_id, file_id, function_id, module_id, normalize_repo_path
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta

GO_FUNCTION_RE = re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
GO_IMPORT_RE = re.compile(r'import\s+(?:\((?P<block>.*?)\)|"(?P<single>[^"]+)")', re.DOTALL)
GO_IMPORT_PATH_RE = re.compile(r'"([^"]+)"')
GO_TYPE_RE = re.compile(r"^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+", re.MULTILINE)
GO_CALL_RE = re.compile(
    r"\b(?P<receiver>[A-Z][A-Za-z0-9]*)\.(?P<method>[A-Za-z][A-Za-z0-9]*)\s*\(|"  # StructType.Method(
    r"\b(?P<func>[A-Z][A-Za-z0-9]*)\s*\(",                                          # ExportedFunc(
    re.MULTILINE,
)
NOISY_GO_CALL_NAMES = {
    "Close",
    "Create",
    "Delete",
    "Error",
    "Execute",
    "Get",
    "List",
    "Name",
    "New",
    "Run",
    "Scan",
    "Set",
    "Start",
    "Stop",
    "String",
    "Update",
}

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
import ast

class PythonVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str, text: str):
        self.relative_path = relative_path
        self.text = text
        self.classes = []
        self.functions = []
        self.imports = []
        self.calls = []
        self.routes = []
        self.current_class = None
        self.current_function = None

    def visit_Import(self, node):
        for name in node.names:
            self.imports.append({
                "module": name.name,
                "lineno": node.lineno
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if node.level and node.level > 0:
            module = "." * node.level + module
        self.imports.append({
            "module": module,
            "lineno": node.lineno
        })
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = node.name
        docstring = ast.get_docstring(node)
        start_line = node.lineno
        end_line = start_line
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                end_line = max(end_line, child.lineno)
        
        class_info = {
            "name": class_name,
            "docstring": docstring,
            "start_line": start_line,
            "end_line": end_line,
        }
        self.classes.append(class_info)
        
        prev_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        self._visit_any_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_any_function(node)

    def _visit_any_function(self, node):
        func_name = node.name
        qualified_name = f"{self.current_class}.{func_name}" if self.current_class else func_name
        docstring = ast.get_docstring(node)
        start_line = node.lineno
        end_line = start_line
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                end_line = max(end_line, child.lineno)
                
        args = [arg.arg for arg in node.args.args]
        
        for dec in node.decorator_list:
            dec_name = ""
            if isinstance(dec, ast.Call):
                func = dec.func
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        dec_name = f"{func.value.id}.{func.attr}"
                    else:
                        dec_name = func.attr
                elif isinstance(func, ast.Name):
                    dec_name = func.id
                
                if dec_name in ["router.get", "router.post", "router.put", "router.delete", "router.patch", "router.route",
                                 "app.get", "app.post", "app.put", "app.delete", "app.patch", "app.route"]:
                    route_path = ""
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        route_path = str(dec.args[0].value)
                    elif dec.args and isinstance(dec.args[0], ast.Str):
                        route_path = str(dec.args[0].s)
                    
                    self.routes.append({
                        "path": route_path,
                        "method": dec_name.split(".")[-1],
                        "handler": qualified_name,
                        "lineno": dec.lineno
                    })

        func_info = {
            "name": func_name,
            "qualified_name": qualified_name,
            "is_method": self.current_class is not None,
            "class_name": self.current_class,
            "docstring": docstring,
            "start_line": start_line,
            "end_line": end_line,
            "signature": f"def {func_name}({', '.join(args)})"
        }
        self.functions.append(func_info)

        prev_func = self.current_function
        self.current_function = qualified_name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node):
        if self.current_function:
            callee = ""
            func = node.func
            if isinstance(func, ast.Name):
                callee = func.id
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    callee = f"{func.value.id}.{func.attr}"
                else:
                    callee = func.attr
            if callee:
                self.calls.append({
                    "caller": self.current_function,
                    "callee": callee,
                    "lineno": node.lineno
                })
        self.generic_visit(node)



TSJS_IMPORT_RE = re.compile(r"^[ \t]*import\s+(?:.*\s+from\s+)?['\"](?P<path>[^'\"]+)['\"]", re.MULTILINE)
DOCUMENT_EXTENSIONS = (".md", ".mdx", ".txt", ".rst")
DOCUMENT_SNIPPET_LIMIT = 2400


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
        settings = get_settings()
        self.call_graph_mode = settings.scan_call_graph_mode.lower()
        self.include_test_calls = settings.scan_include_test_calls

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

        go_files: list[tuple[Path, str, str]] = []
        python_files: list[tuple[Path, str, str]] = []
        for path in sorted(self.repo_path.rglob("*")):
            if not path.is_file():
                continue
            relative = normalize_repo_path(str(path.relative_to(self.repo_path)))
            if self._is_excluded(relative):
                continue
            text = self._add_file(store, path, relative)
            if text is not None:
                if relative.endswith(".go"):
                    go_files.append((path, relative, text))
                elif relative.endswith((".py", ".pyw")):
                    python_files.append((path, relative, text))

        if self.call_graph_mode != "off":
            self._add_go_call_graph(store, go_files)
            self._add_python_call_graph(store, python_files)

        return store.graph

    def _is_excluded(self, relative_path: str) -> bool:
        parts = relative_path.split("/")
        return any(
            fnmatch.fnmatch(relative_path, pattern)
            or any(fnmatch.fnmatch(part, pattern) for part in parts)
            for pattern in self.exclude_patterns
        )

    def _add_file(self, store: GraphStore, path: Path, relative: str) -> str | None:
        text_for_metadata = self._read_indexable_text(path, relative)
        metadata = {"language": self._language_for(relative)}
        if text_for_metadata and self._is_document(relative):
            metadata.update(
                {
                    "document_snippet": self._document_snippet(text_for_metadata),
                    "evidence_type": "doc",
                }
            )
        file_node = GraphNode(
            id=file_id(relative),
            type="file",
            name=Path(relative).name,
            summary=self._file_summary(relative, text_for_metadata),
            tags=self._file_tags(relative),
            filePath=relative,
            metadata=metadata,
        )
        store.upsert_node(file_node)
        self._add_modules(store, relative, file_node.id)

        if relative.endswith(".go"):
            text = text_for_metadata or path.read_text(encoding="utf-8", errors="ignore")
            self._add_go_symbols(store, relative, text, file_node.id)
            self._add_go_import_edges(store, relative, text, file_node.id)
            return text
        elif relative.endswith((".py", ".pyw")):
            text = text_for_metadata or path.read_text(encoding="utf-8", errors="ignore")
            self._add_python_symbols(store, relative, text, file_node.id)
            self._add_python_import_edges(store, relative, text, file_node.id)
            return text
        elif relative.endswith((".ts", ".tsx", ".js", ".jsx")):
            text = text_for_metadata or path.read_text(encoding="utf-8", errors="ignore")
            self._add_tsjs_symbols(store, relative, text, file_node.id)
            self._add_tsjs_import_edges(store, relative, text, file_node.id)
        return None

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

    def _line_of(self, text: str, match_start: int) -> int:
        """Return 1-indexed line number for a match position in text."""
        return text[:match_start].count("\n") + 1

    def _add_go_call_graph(self, store: GraphStore, go_files: list[tuple[Path, str, str]]) -> None:
        functions_by_file: dict[str, set[str]] = defaultdict(set)
        functions_by_package: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for _, relative, text in go_files:
            package_path = self._go_package_path(relative)
            for match in GO_FUNCTION_RE.finditer(text):
                name = match.group("name")
                fid = function_id(relative, name)
                functions_by_file[relative].add(fid)
                functions_by_package[package_path][name].add(fid)

        for _, relative, text in go_files:
            if not self.include_test_calls and self._is_test_file(relative):
                continue
            self._add_go_call_edges(
                store,
                relative,
                text,
                functions_by_file=functions_by_file,
                functions_by_package=functions_by_package,
            )

    def _add_go_call_edges(
        self,
        store: GraphStore,
        relative: str,
        text: str,
        *,
        functions_by_file: dict[str, set[str]],
        functions_by_package: dict[str, dict[str, set[str]]],
    ) -> None:
        """
        Create approximate `calls` edges between functions in the same file
        and exported functions called from other files.
        Only links calls where the callee already exists as a graph node —
        avoids creating dangling references to stdlib or vendor functions.
        """
        same_file_functions = functions_by_file.get(relative, set())
        same_package_functions = functions_by_package.get(self._go_package_path(relative), {})
        # Find all function definitions in this file to use as callers
        caller_ranges: list[tuple[str, int, int]] = []
        lines = text.splitlines()
        total_lines = len(lines)
        for match in GO_FUNCTION_RE.finditer(text):
            fname = match.group("name")
            fid = function_id(relative, fname)
            start_line = self._line_of(text, match.start())
            caller_ranges.append((fid, start_line, total_lines))

        # Assign each function an end line (start of next function - 1)
        for i in range(len(caller_ranges) - 1):
            caller_ranges[i] = (
                caller_ranges[i][0],
                caller_ranges[i][1],
                caller_ranges[i + 1][1] - 1,
            )

        for caller_id, start, end in caller_ranges:
            body_lines = lines[start - 1 : end]
            body_text = "\n".join(body_lines)
            seen_callees: set[str] = set()
            for m in GO_CALL_RE.finditer(body_text):
                callee_name = m.group("method") or m.group("func")
                if not callee_name:
                    continue
                target_id = self._resolve_go_callee(
                    callee_name,
                    caller_id,
                    same_file_functions,
                    same_package_functions,
                )
                if not target_id or target_id in seen_callees:
                    continue
                seen_callees.add(target_id)
                store.upsert_edge(
                    GraphEdge(
                        id=edge_id(caller_id, target_id, "calls"),
                        source=caller_id,
                        target=target_id,
                        type="calls",
                        summary=f"{caller_id.split(':')[-1]} calls {callee_name}.",
                        weight=0.8,
                    )
                )

    def _resolve_go_callee(
        self,
        callee_name: str,
        caller_id: str,
        same_file_functions: set[str],
        same_package_functions: dict[str, set[str]],
    ) -> str | None:
        same_file_target = next(
            (
                fid
                for fid in same_file_functions
                if fid.endswith(f":{callee_name}") and fid != caller_id
            ),
            None,
        )
        if same_file_target:
            return same_file_target
        if self.call_graph_mode != "package" or callee_name in NOISY_GO_CALL_NAMES:
            return None
        package_targets = {
            fid for fid in same_package_functions.get(callee_name, set()) if fid != caller_id
        }
        if len(package_targets) == 1:
            return next(iter(package_targets))
        return None

    def _go_package_path(self, relative: str) -> str:
        parent = Path(relative).parent
        return "" if str(parent) == "." else normalize_repo_path(str(parent))

    def _is_test_file(self, relative: str) -> bool:
        return relative.endswith("_test.go") or relative.startswith("tests/")

    def _add_go_symbols(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        for match in GO_FUNCTION_RE.finditer(text):
            name = match.group("name")
            line_no = self._line_of(text, match.start())
            node = GraphNode(
                id=function_id(relative, name),
                type="function",
                name=name,
                summary=f"Go function {name} in {relative}.",
                tags=["go", "function"],
                filePath=relative,
                line_range=(line_no, line_no),
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
            line_no = self._line_of(text, match.start())
            node = GraphNode(
                id=f"class:{relative}:{name}",
                type="class",
                name=name,
                summary=f"Go type {name} in {relative}.",
                tags=["go", "type"],
                filePath=relative,
                line_range=(line_no, line_no),
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
        try:
            tree = ast.parse(text)
        except Exception:
            return  # Skip if invalid syntax

        visitor = PythonVisitor(relative, text)
        visitor.visit(tree)

        # 1. Upsert Class nodes and contain edges
        for cls in visitor.classes:
            class_name = cls["name"]
            node = GraphNode(
                id=f"class:{relative}:{class_name}",
                type="class",
                name=class_name,
                summary=cls["docstring"] or f"Python class {class_name} in {relative}.",
                tags=["python", "class"],
                filePath=relative,
                line_range=(cls["start_line"], cls["end_line"]),
                metadata={
                    "language": "python",
                    "docstring": cls["docstring"],
                },
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

        # 2. Upsert Function / Method nodes and contain edges
        for func in visitor.functions:
            func_name = func["name"]
            qualified_name = func["qualified_name"]
            node = GraphNode(
                id=function_id(relative, qualified_name),
                type="function",
                name=func_name,
                summary=func["docstring"] or f"Python function {qualified_name} in {relative}.",
                tags=["python", "method" if func["is_method"] else "function"],
                filePath=relative,
                line_range=(func["start_line"], func["end_line"]),
                metadata={
                    "language": "python",
                    "qualified_name": qualified_name,
                    "signature": func["signature"],
                    "docstring": func["docstring"],
                },
            )
            store.upsert_node(node)

            # Link parent
            if func["is_method"]:
                parent_id = f"class:{relative}:{func['class_name']}"
                summary = "Class contains method."
            else:
                parent_id = file_node_id
                summary = "File contains function."

            store.upsert_edge(
                GraphEdge(
                    id=edge_id(parent_id, node.id, "contains"),
                    source=parent_id,
                    target=node.id,
                    type="contains",
                    summary=summary,
                    weight=1.0,
                )
            )

        # 3. Upsert Endpoint nodes and routes edges
        for route in visitor.routes:
            endpoint_id = f"endpoint:{route['method']}:{route['path']}"
            handler_id = function_id(relative, route['handler'])
            
            node = GraphNode(
                id=endpoint_id,
                type="endpoint",
                name=f"{route['method'].upper()} {route['path']}",
                summary=f"FastAPI endpoint {route['method'].upper()} {route['path']}.",
                tags=["fastapi", "endpoint", route["method"].lower()],
                filePath=relative,
                line_range=(route["lineno"], route["lineno"]),
                metadata={"language": "python", "method": route["method"], "path": route["path"]},
            )
            store.upsert_node(node)
            
            store.upsert_edge(
                GraphEdge(
                    id=edge_id(endpoint_id, handler_id, "routes"),
                    source=endpoint_id,
                    target=handler_id,
                    type="routes",
                    summary=f"Route {route['method'].upper()} {route['path']} handled by {route['handler']}.",
                    weight=1.0,
                )
            )

    def _add_python_import_edges(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        try:
            tree = ast.parse(text)
        except Exception:
            return  # Skip if invalid syntax

        visitor = PythonVisitor(relative, text)
        visitor.visit(tree)

        imported_modules = set(imp["module"] for imp in visitor.imports if imp["module"])

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

    def _add_python_call_graph(self, store: GraphStore, python_files: list[tuple[Path, str, str]]) -> None:
        from collections import defaultdict
        functions_by_file = defaultdict(set)
        functions_globally = defaultdict(set)
        
        visitors = {}
        for _, relative, text in python_files:
            try:
                tree = ast.parse(text)
                visitor = PythonVisitor(relative, text)
                visitor.visit(tree)
                visitors[relative] = visitor
                
                for f in visitor.functions:
                    qname = f["qualified_name"]
                    fid = function_id(relative, qname)
                    functions_by_file[relative].add(qname)
                    functions_globally[qname].add(fid)
                    last_part = qname.split(".")[-1]
                    functions_globally[last_part].add(fid)
                    if "." in qname:
                        functions_globally[qname.split(".")[-2] + "." + last_part].add(fid)
            except Exception:
                pass

        for _, relative, text in python_files:
            visitor = visitors.get(relative)
            if not visitor:
                continue
            
            for call in visitor.calls:
                caller_qname = call["caller"]
                callee_name = call["callee"]
                caller_id = function_id(relative, caller_qname)
                
                resolved_id = None
                
                if "." in caller_qname and callee_name.startswith("self."):
                    class_name = caller_qname.split(".")[0]
                    method_name = callee_name.split(".", 1)[1]
                    target_qname = f"{class_name}.{method_name}"
                    if target_qname in functions_by_file[relative]:
                        resolved_id = function_id(relative, target_qname)
                
                if not resolved_id and callee_name in functions_by_file[relative]:
                    resolved_id = function_id(relative, callee_name)
                
                if not resolved_id:
                    targets = functions_globally.get(callee_name, set())
                    if len(targets) == 1:
                        resolved_id = next(iter(targets))
                    elif not targets:
                        last_part = callee_name.split(".")[-1]
                        targets_last = functions_globally.get(last_part, set())
                        if len(targets_last) == 1:
                            resolved_id = next(iter(targets_last))
                
                if resolved_id:
                    store.upsert_edge(
                        GraphEdge(
                            id=edge_id(caller_id, resolved_id, "calls"),
                            source=caller_id,
                            target=resolved_id,
                            type="calls",
                            summary=f"{caller_qname.split('.')[-1]} calls {callee_name.split('.')[-1]}.",
                            weight=0.8,
                        )
                    )
                else:
                    try:
                        caller_node = store.graph.node_by_id(caller_id)
                        if caller_node:
                            unresolved = caller_node.metadata.setdefault("unresolved_calls", [])
                            if callee_name not in unresolved:
                                unresolved.append(callee_name)
                    except Exception:
                        pass

    def _add_tsjs_symbols(self, store: GraphStore, relative: str, text: str, file_node_id: str) -> None:
        for match in TSJS_FUNCTION_RE.finditer(text):
            name = match.group("name") or match.group("arrow_name")
            if not name:
                continue
            line_no = self._line_of(text, match.start())
            node = GraphNode(
                id=function_id(relative, name),
                type="function",
                name=name,
                summary=f"JavaScript/TypeScript function {name} in {relative}.",
                tags=["javascript", "typescript", "function"],
                filePath=relative,
                line_range=(line_no, line_no),
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
            line_no = self._line_of(text, match.start())
            node = GraphNode(
                id=f"class:{relative}:{name}",
                type="class",
                name=name,
                summary=f"JavaScript/TypeScript class {name} in {relative}.",
                tags=["javascript", "typescript", "class"],
                filePath=relative,
                line_range=(line_no, line_no),
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

    def _file_summary(self, relative: str, text: str | None = None) -> str:
        if self._is_document(relative):
            heading = self._first_heading(text or "")
            if heading:
                return f"Documentation file {relative}: {heading}."
            return f"Documentation file {relative}."
        lang = self._language_for(relative)
        if lang:
            return f"{lang.capitalize()} source file {relative}."
        if relative.lower().endswith((".json", ".yaml", ".yml", ".toml")):
            return f"Configuration file {relative}."
        return f"Repository file {relative}; detailed symbols unavailable."

    def _is_document(self, relative: str) -> bool:
        return relative.lower().endswith(DOCUMENT_EXTENSIONS)

    def _read_indexable_text(self, path: Path, relative: str) -> str | None:
        if relative.endswith((".go", ".py", ".pyw", ".ts", ".tsx", ".js", ".jsx")) or self._is_document(relative):
            return path.read_text(encoding="utf-8", errors="ignore")
        return None

    def _first_heading(self, text: str) -> str | None:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()[:160]
            return stripped[:160]
        return None

    def _document_snippet(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("<!--"):
                continue
            lines.append(stripped)
            if sum(len(item) for item in lines) >= DOCUMENT_SNIPPET_LIMIT:
                break
        return " ".join(lines)[:DOCUMENT_SNIPPET_LIMIT]


    def _file_tags(self, relative: str) -> list[str]:
        tags = ["file"]
        language = self._language_for(relative)
        if language:
            tags.append(language)
        if self._is_document(relative):
            tags.extend(["doc", "markdown" if relative.lower().endswith((".md", ".mdx")) else "text"])
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
