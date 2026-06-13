import re

from backend.app.graph.ids import claim_id, edge_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph

RATIONALE_PATTERNS = [
    re.compile(r"\bbecause\b(?P<claim>.+)", re.IGNORECASE),
    re.compile(r"\bso that\b(?P<claim>.+)", re.IGNORECASE),
    re.compile(r"\bin order to\b(?P<claim>.+)", re.IGNORECASE),
    re.compile(r"\btradeoff\b[:\-]?(?P<claim>.+)", re.IGNORECASE),
    re.compile(r"\brisk\b[:\-]?(?P<claim>.+)", re.IGNORECASE),
    re.compile(r"\bmigration\b[:\-]?(?P<claim>.+)", re.IGNORECASE),
]


class RationaleExtractor:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def extract(self) -> KnowledgeGraph:
        for source in list(self.graph.nodes):
            if source.type != "source":
                continue
            claim_text = self._extract_claim_text(source.summary)
            if not claim_text:
                continue
            claim = GraphNode(
                id=claim_id(claim_text),
                type="claim",
                name=self._claim_name(claim_text),
                summary=claim_text,
                tags=self._claim_tags(claim_text),
                metadata={
                    "confidence": 0.72,
                    "extractedFrom": [source.id],
                    "method": "explicit-pattern",
                },
            )
            self._upsert_claim(claim, source.id)
        return self.graph

    def _extract_claim_text(self, text: str) -> str | None:
        compact = " ".join(text.split())
        for pattern in RATIONALE_PATTERNS:
            match = pattern.search(compact)
            if not match:
                continue
            claim = match.group("claim").strip(" .:-")
            if len(claim) < 12:
                return None
            return claim[0].upper() + claim[1:] + "."
        return None

    def _claim_name(self, claim_text: str) -> str:
        return claim_text[:80].rstrip(".")

    def _claim_tags(self, claim_text: str) -> list[str]:
        tags = ["design-rationale"]
        lowered = claim_text.lower()
        if "risk" in lowered:
            tags.append("risk")
        if "test" in lowered:
            tags.append("testability")
        if "migration" in lowered:
            tags.append("migration")
        if "performance" in lowered:
            tags.append("performance")
        if "security" in lowered:
            tags.append("security")
        return tags

    def _upsert_claim(self, claim: GraphNode, source_id: str) -> None:
        if not any(node.id == claim.id for node in self.graph.nodes):
            self.graph.nodes.append(claim)
        edge = GraphEdge(
            id=edge_id(source_id, claim.id, "exemplifies"),
            source=source_id,
            target=claim.id,
            type="exemplifies",
            summary="Source evidence demonstrates extracted rationale claim.",
            weight=0.8,
        )
        if not any(existing.id == edge.id for existing in self.graph.edges):
            self.graph.edges.append(edge)
        self.graph.nodes.sort(key=lambda node: node.id)
        self.graph.edges.sort(key=lambda edge: edge.id)
