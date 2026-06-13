from typing import Literal

from backend.app.graph.ids import file_id
from backend.app.graph.models import KnowledgeGraph
from backend.app.services.retrieval import RetrievalService

Purpose = Literal["pr_review", "ai_agent_context"]


class EvidencePackService:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        self.retrieval = RetrievalService(graph)

    def create(
        self,
        purpose: Purpose,
        query: str | None = None,
        node_ids: list[str] | None = None,
        changed_files: list[str] | None = None,
        allow_external_llm_for_private_repo: bool = False,
    ) -> dict[str, object]:
        seed_ids = list(node_ids or []) + [file_id(path) for path in changed_files or []]
        result = self.retrieval.answer(
            query=query or "Create evidence pack",
            mode="hybrid",
            node_ids=seed_ids,
        )
        citations = result.citations
        warnings = list(result.warnings)
        if allow_external_llm_for_private_repo is False:
            warnings.append("External LLM disabled for this repository. Generated evidence-only pack.")
        markdown = self._markdown(purpose, result.structural, result.historical, warnings, citations)
        return {
            "purpose": purpose,
            "markdown": markdown,
            "citations": citations,
            "warnings": warnings,
            "excluded_sources": [],
            "evidence_only": True,
        }

    def _markdown(
        self,
        purpose: Purpose,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        warnings: list[str],
        citations: list[dict[str, object]],
    ) -> str:
        if purpose == "pr_review":
            sections = [
                "# PR Review Evidence Pack",
                "## Changed scope",
                self._items(structural),
                "## Structural impact",
                self._items(structural),
                "## Historical context",
                self._items(historical),
                "## Risks / review questions",
                self._warnings(warnings),
                "## Citations",
                self._items(citations),
            ]
        else:
            sections = [
                "# AI-Agent Context Pack",
                "## Task context",
                self._items(structural),
                "## Relevant files/interfaces",
                self._items(structural),
                "## Historical constraints",
                self._items(historical),
                "## Do not assume",
                self._warnings(warnings),
                "## Citations",
                self._items(citations),
            ]
        return "\n\n".join(sections)

    def _items(self, evidence: list[dict[str, object]]) -> str:
        if not evidence:
            return "- No evidence found."
        return "\n".join(f"- {item['label']}: {item['summary']}" for item in evidence)

    def _warnings(self, warnings: list[str]) -> str:
        if not warnings:
            return "- No warnings."
        return "\n".join(f"- {warning}" for warning in warnings)
