import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph, RepoMeta


class GraphStore:
    def __init__(self, path: Path, repo: RepoMeta, graph: KnowledgeGraph | None = None) -> None:
        self.path = path
        self.graph = graph or KnowledgeGraph(repo=repo)

    @classmethod
    def load(cls, path: Path) -> "GraphStore":
        payload = json.loads(path.read_text(encoding="utf-8"))
        graph = KnowledgeGraph.model_validate(payload)
        return cls(path=path, repo=graph.repo, graph=graph)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.generated_at = datetime.now(timezone.utc)
        self.path.write_text(
            self.graph.model_dump_json(by_alias=True, indent=2),
            encoding="utf-8",
        )

    def upsert_node(self, node: GraphNode) -> GraphNode:
        for index, existing in enumerate(self.graph.nodes):
            if existing.id == node.id:
                merged = self._merge_node(existing, node)
                self.graph.nodes[index] = merged
                self._sort_graph()
                return merged
        self.graph.nodes.append(node)
        self._sort_graph()
        return node

    def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        for index, existing in enumerate(self.graph.edges):
            if existing.id == edge.id:
                merged = self._merge_edge(existing, edge)
                self.graph.edges[index] = merged
                self._sort_graph()
                return merged
        self.graph.edges.append(edge)
        self._sort_graph()
        return edge

    def merge(self, other: KnowledgeGraph) -> KnowledgeGraph:
        for node in other.nodes:
            self.upsert_node(node)
        for edge in other.edges:
            self.upsert_edge(edge)
        return self.graph

    def _merge_node(self, existing: GraphNode, incoming: GraphNode) -> GraphNode:
        return existing.model_copy(
            update={
                "name": incoming.name or existing.name,
                "summary": incoming.summary or existing.summary,
                "tags": sorted(set(existing.tags).union(incoming.tags)),
                "file_path": incoming.file_path or existing.file_path,
                "line_range": incoming.line_range or existing.line_range,
                "metadata": {**existing.metadata, **incoming.metadata},
            }
        )

    def _merge_edge(self, existing: GraphEdge, incoming: GraphEdge) -> GraphEdge:
        return existing.model_copy(
            update={
                "summary": incoming.summary or existing.summary,
                "weight": max(existing.weight, incoming.weight),
                "metadata": {**existing.metadata, **incoming.metadata},
            }
        )

    def _sort_graph(self) -> None:
        self.graph.nodes.sort(key=lambda node: node.id)
        self.graph.edges.sort(key=lambda edge: edge.id)
