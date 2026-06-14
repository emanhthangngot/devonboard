from typing import Literal

from backend.app.graph.ids import file_id
from backend.app.graph.models import KnowledgeGraph
from backend.app.services.retrieval import RetrievalService, STRUCTURAL_TYPES

Purpose = Literal["pr_review", "ai_agent_context"]

# Patterns for files that should be excluded from evidence packs.
_EXCLUDED_PATTERNS = {
    ".env", ".env.local", ".env.production",
    "node_modules/", "vendor/", "dist/", "build/", ".git/",
    "__pycache__/", ".venv/", ".uv-cache/",
}


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
        changed_file_ids = {file_id(path) for path in changed_files or []}

        result = self.retrieval.answer(
            query=query or "Create evidence pack",
            mode="hybrid",
            node_ids=seed_ids,
            allow_external_llm=allow_external_llm_for_private_repo,
        )

        # Separate changed-scope items from blast-radius items.
        changed_scope = [
            item for item in result.structural
            if str(item.get("node_id", "")) in changed_file_ids
        ]
        blast_radius = [
            item for item in result.structural
            if str(item.get("node_id", "")) not in changed_file_ids
        ]
        # If no changed files were specified, treat all structural as scope.
        if not changed_files:
            changed_scope = result.structural
            blast_radius = []

        # Filter out secrets, generated, and vendor files.
        filtered_structural = self._filter_excluded(result.structural)
        filtered_changed = self._filter_excluded(changed_scope)
        filtered_blast = self._filter_excluded(blast_radius)
        excluded_sources = self._find_excluded(result.structural)

        citations = result.citations
        warnings = list(result.warnings)
        if not allow_external_llm_for_private_repo:
            warnings.append("External LLM disabled for this repository. Generated evidence-only pack.")

        markdown = self._markdown(
            purpose, filtered_changed, filtered_blast,
            result.historical, warnings, citations,
        )
        return {
            "purpose": purpose,
            "markdown": markdown,
            "citations": citations,
            "warnings": warnings,
            "excluded_sources": excluded_sources,
            "evidence_only": not allow_external_llm_for_private_repo,
        }

    def _markdown(
        self,
        purpose: Purpose,
        changed_scope: list[dict[str, object]],
        blast_radius: list[dict[str, object]],
        historical: list[dict[str, object]],
        warnings: list[str],
        citations: list[dict[str, object]],
    ) -> str:
        if purpose == "pr_review":
            sections = [
                "# PR Review Evidence Pack",
                "## Changed scope",
                self._items(changed_scope),
                "## Structural impact",
                self._items(blast_radius) if blast_radius else "- No additional structural impact beyond changed files.",
                "## Historical context",
                self._items(historical),
                "## Risks / review questions",
                self._warnings(warnings),
                "## Citations",
                self._items(citations),
            ]
        else:
            # Extract interfaces and constraints separately.
            interfaces = [
                item for item in changed_scope
                if str(item.get("type", "")) in {"function", "class", "endpoint", "service"}
            ]
            files = [
                item for item in changed_scope
                if str(item.get("type", "")) in {"file", "module", "config"}
            ]
            sections = [
                "# AI-Agent Context Pack",
                "## Task context",
                self._items(files or changed_scope),
                "## Relevant files/interfaces",
                self._items(interfaces) if interfaces else self._items(blast_radius or changed_scope),
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

    def _filter_excluded(self, evidence: list[dict[str, object]]) -> list[dict[str, object]]:
        """Remove items whose node_id references excluded paths (secrets, vendor, generated)."""
        return [item for item in evidence if not self._is_excluded(str(item.get("node_id", "")))]

    def _find_excluded(self, evidence: list[dict[str, object]]) -> list[str]:
        """Return node IDs of items that were excluded."""
        return [str(item.get("node_id", "")) for item in evidence if self._is_excluded(str(item.get("node_id", "")))]

    def _is_excluded(self, node_id: str) -> bool:
        lowered = node_id.lower()
        return any(pattern in lowered for pattern in _EXCLUDED_PATTERNS)
