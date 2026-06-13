from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NodeType = Literal[
    "file",
    "function",
    "class",
    "module",
    "service",
    "endpoint",
    "config",
    "domain",
    "flow",
    "step",
    "source",
    "claim",
    "entity",
    "topic",
]

EdgeType = Literal[
    "contains",
    "imports",
    "calls",
    "depends_on",
    "implements",
    "routes",
    "configures",
    "contains_flow",
    "flow_step",
    "cites",
    "documents",
    "authored_by",
    "exemplifies",
    "builds_on",
    "contradicts",
    "related",
]


class RepoMeta(BaseModel):
    name: str
    path: str
    branch: str = "dev"
    commit: str | None = None
    url: str | None = None


class ResultRunSummary(BaseModel):
    run_id: str
    created_at: datetime


class GraphNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: NodeType
    name: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    file_path: str | None = Field(default=None, alias="filePath")
    line_range: tuple[int, int] | None = Field(default=None, alias="lineRange")
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType
    summary: str | None = None
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    version: str = "0.1.0"
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="generated_at"
    )
    repo: RepoMeta
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    result_runs: list[ResultRunSummary] = Field(default_factory=list)

    def node_by_id(self, node_id: str) -> GraphNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)
