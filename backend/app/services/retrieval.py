import time
from dataclasses import dataclass
from typing import Literal

from backend.app.graph.models import GraphNode, KnowledgeGraph

Route = Literal["structural", "historical", "hybrid"]

STRUCTURAL_TYPES = {"file", "function", "class", "module", "service", "endpoint", "config", "domain", "flow", "step"}
HISTORICAL_TYPES = {"source", "claim", "entity", "topic"}


@dataclass
class QueryResult:
    answer: str
    route: Route
    structural: list[dict[str, object]]
    historical: list[dict[str, object]]
    citations: list[dict[str, object]]
    warnings: list[str]
    retrieval_ms: int
    synthesis_ms: int
    evidence_only: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "answer": self.answer,
            "route": self.route,
            "structural": self.structural,
            "historical": self.historical,
            "citations": self.citations,
            "warnings": self.warnings,
            "retrieval_ms": self.retrieval_ms,
            "synthesis_ms": self.synthesis_ms,
            "evidence_only": self.evidence_only,
        }


class RetrievalService:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def answer(self, query: str, mode: str = "auto", node_ids: list[str] | None = None) -> QueryResult:
        start = time.perf_counter()
        route = self._route(query, mode)
        structural_nodes = self._structural_matches(query, node_ids)
        historical_nodes = self._historical_matches(structural_nodes, query)
        retrieval_ms = int((time.perf_counter() - start) * 1000)

        structural = [self._evidence(node) for node in structural_nodes[:5]]
        historical = [self._evidence(node) for node in historical_nodes[:8]]
        citations = self._dedupe_evidence(structural + historical)
        warnings: list[str] = []
        if route in {"historical", "hybrid"} and not historical:
            warnings.append("No historical evidence found for this query.")
        if route in {"structural", "hybrid"} and not structural:
            warnings.append("No structural evidence found for this query.")

        synth_start = time.perf_counter()
        answer = self._synthesize(route, structural, historical, warnings)
        synthesis_ms = int((time.perf_counter() - synth_start) * 1000)
        return QueryResult(
            answer=answer,
            route=route,
            structural=structural,
            historical=historical,
            citations=citations,
            warnings=warnings,
            retrieval_ms=retrieval_ms,
            synthesis_ms=synthesis_ms,
            evidence_only=False,
        )

    def node_history(self, node_id: str) -> dict[str, object]:
        source_ids = {
            edge.source
            for edge in self.graph.edges
            if edge.target == node_id and edge.type in {"documents", "cites"}
        }
        claim_ids = {
            edge.target
            for edge in self.graph.edges
            if edge.source in source_ids and edge.type == "exemplifies"
        }
        evidence = [self._evidence(node) for node in self.graph.nodes if node.id in source_ids]
        claims = [self._evidence(node) for node in self.graph.nodes if node.id in claim_ids]
        risks = [
            self._evidence(node)
            for node in self.graph.nodes
            if node.id in claim_ids and any(tag in {"risk", "compatibility"} for tag in node.tags)
        ]
        return {
            "node_id": node_id,
            "evidence": evidence,
            "claims": claims,
            "risks": risks,
            "warnings": [] if evidence or claims else ["No linked commits/PRs found for this node."],
        }

    def _route(self, query: str, mode: str) -> Route:
        if mode in {"structural", "historical", "hybrid"}:
            return mode  # type: ignore[return-value]
        lowered = query.lower()
        if any(token in lowered for token in ["refactor", "safe", "risk", "review", "context pack"]):
            return "hybrid"
        if any(token in lowered for token in ["why", "rationale", "decision", "chosen"]):
            return "historical"
        return "structural"

    def _structural_matches(self, query: str, node_ids: list[str] | None) -> list[GraphNode]:
        if node_ids:
            explicit = [node for node in self.graph.nodes if node.id in set(node_ids)]
            if explicit:
                return explicit
        terms = self._terms(query)
        matches = [
            node
            for node in self.graph.nodes
            if node.type in STRUCTURAL_TYPES and self._node_matches(node, terms)
        ]
        return matches or [node for node in self.graph.nodes if node.type in STRUCTURAL_TYPES][:5]

    def _historical_matches(self, structural_nodes: list[GraphNode], query: str) -> list[GraphNode]:
        terms = self._terms(query)
        structural_ids = {node.id for node in structural_nodes}
        source_ids = {
            edge.source
            for edge in self.graph.edges
            if edge.target in structural_ids and edge.type in {"documents", "cites"}
        }
        claim_ids = {
            edge.target
            for edge in self.graph.edges
            if edge.source in source_ids and edge.type == "exemplifies"
        }
        linked = [node for node in self.graph.nodes if node.id in source_ids.union(claim_ids)]
        textual = [
            node
            for node in self.graph.nodes
            if node.type in HISTORICAL_TYPES and self._node_matches(node, terms)
        ]
        return self._dedupe_nodes(linked + textual)

    def _terms(self, query: str) -> set[str]:
        return {term.strip(".,:;!?()[]{}").lower() for term in query.split() if len(term) > 2}

    def _node_matches(self, node: GraphNode, terms: set[str]) -> bool:
        haystack = " ".join([node.id, node.name, node.summary, *node.tags]).lower()
        return any(term in haystack for term in terms)

    def _evidence(self, node: GraphNode) -> dict[str, object]:
        evidence_type = node.type
        if node.type == "source":
            evidence_type = str(node.metadata.get("kind", "commit"))
        return {
            "node_id": node.id,
            "type": evidence_type,
            "label": node.name,
            "summary": node.summary,
            "url": node.metadata.get("url"),
            "score": node.metadata.get("confidence"),
        }

    def _synthesize(
        self,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        warnings: list[str],
    ) -> str:
        if route == "hybrid":
            return "\n\n".join(
                [
                    "**Structural impact**\n" + self._summarize("structural", structural),
                    "**Historical context**\n" + self._summarize("historical", historical),
                    "**Refactor guidance**\nUse the cited files and claims as the review boundary. Do not assume missing rationale.",
                ]
            )
        if route == "historical":
            return "**Historical context**\n" + self._summarize("historical", historical)
        return "**Structural impact**\n" + self._summarize("structural", structural) + (
            "\n\n" + "\n".join(warnings) if warnings else ""
        )

    def _summarize(self, label: str, evidence: list[dict[str, object]]) -> str:
        if not evidence:
            return f"No {label} evidence found for this query."
        return "\n".join(f"- {item['label']}: {item['summary']}" for item in evidence[:5])

    def _dedupe_nodes(self, nodes: list[GraphNode]) -> list[GraphNode]:
        seen: set[str] = set()
        result: list[GraphNode] = []
        for node in nodes:
            if node.id in seen:
                continue
            seen.add(node.id)
            result.append(node)
        return result

    def _dedupe_evidence(self, evidence: list[dict[str, object]]) -> list[dict[str, object]]:
        seen: set[str] = set()
        result: list[dict[str, object]] = []
        for item in evidence:
            node_id = str(item["node_id"])
            if node_id in seen:
                continue
            seen.add(node_id)
            result.append(item)
        return result
