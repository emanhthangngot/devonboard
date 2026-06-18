import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta


class GraphStore:
    def __init__(self, path: Path, repo: RepoMeta, graph: KnowledgeGraph | None = None) -> None:
        self.path = path
        self.graph = graph or KnowledgeGraph(repo=repo)
        self._nodes_by_id = {node.id: node for node in self.graph.nodes}
        self._edges_by_id = {edge.id: edge for edge in self.graph.edges}

    @classmethod
    def load(cls, path: Path) -> "GraphStore":
        payload = json.loads(path.read_text(encoding="utf-8"))
        graph = KnowledgeGraph.model_validate(payload)
        return cls(path=path, repo=graph.repo, graph=graph)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.nodes.sort(key=lambda node: node.id)
        self.graph.edges.sort(key=lambda edge: edge.id)
        self.graph.generated_at = datetime.now(timezone.utc)
        self.path.write_text(
            self.graph.model_dump_json(by_alias=True, indent=2),
            encoding="utf-8",
        )

    def upsert_node(self, node: GraphNode) -> GraphNode:
        if node.id in self._nodes_by_id:
            existing = self._nodes_by_id[node.id]
            existing.name = node.name or existing.name
            existing.summary = node.summary or existing.summary
            existing.tags = sorted(set(existing.tags).union(node.tags))
            existing.file_path = node.file_path or existing.file_path
            existing.line_range = node.line_range or existing.line_range
            existing.metadata = {**existing.metadata, **node.metadata}
            return existing
        else:
            self._nodes_by_id[node.id] = node
            self.graph.nodes.append(node)
            return node

    def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        if edge.id in self._edges_by_id:
            existing = self._edges_by_id[edge.id]
            existing.summary = edge.summary or existing.summary
            existing.weight = max(existing.weight, edge.weight)
            existing.metadata = {**existing.metadata, **edge.metadata}
            return existing
        else:
            self._edges_by_id[edge.id] = edge
            self.graph.edges.append(edge)
            return edge

    def merge(self, other: KnowledgeGraph) -> KnowledgeGraph:
        for node in other.nodes:
            self.upsert_node(node)
        for edge in other.edges:
            self.upsert_edge(edge)
        self.graph.nodes.sort(key=lambda node: node.id)
        self.graph.edges.sort(key=lambda edge: edge.id)
        return self.graph
