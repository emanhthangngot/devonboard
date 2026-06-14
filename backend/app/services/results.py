import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.graph.models import KnowledgeGraph
from backend.app.services.retrieval import QueryResult, RetrievalService, STRUCTURAL_TYPES, HISTORICAL_TYPES

RESULT_QUERIES = [
    "How does the agent pipeline execute a tool call?",
    "Why was progressive memory loading chosen?",
    "Is it safe to refactor ProviderAdapter?",
    "What should I inspect before reviewing changes touching ProviderAdapter?",
    "Create a cited context pack for an agent modifying the provider subsystem.",
]


class ResultService:
    def __init__(self, graph: KnowledgeGraph, results_dir: Path | None = None) -> None:
        self.graph = graph
        self.results_dir = results_dir or Path(os.environ.get("DEVONBOARD_RESULTS_DIR", "./devonboard/results"))

    def run(self, repo: str, target_branch: str, target_commit: str | None = None) -> dict[str, object]:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
        retrieval = RetrievalService(self.graph)
        rows: list[dict[str, object]] = []
        for index, query in enumerate(RESULT_QUERIES, start=1):
            result = retrieval.answer(query=query, mode="auto")
            rows.append(
                {
                    "query_id": index,
                    "query_text": query,
                    "time_to_useful_answer_ms": result.retrieval_ms + result.synthesis_ms,
                    "citations_count": len(result.citations),
                    "evidence_count": len(result.structural) + len(result.historical),
                    "warnings_count": len(result.warnings),
                    "evidence_usefulness_score": self._evidence_usefulness_score(result),
                    "human_quality_score": None,
                }
            )
        run = {
            "run_id": run_id,
            "repo": repo,
            "target_branch": target_branch,
            "target_commit": target_commit,
            "rows": rows,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / f"{run_id}.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
        return run

    def list_runs(self) -> list[dict[str, object]]:
        if not self.results_dir.exists():
            return []
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.results_dir.glob("*.json"), reverse=True)
        ]

    def get_run(self, run_id: str) -> dict[str, object] | None:
        path = self.results_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _evidence_usefulness_score(self, result: QueryResult) -> int:
        """Deterministic 1-5 score per RAG.md §8.

        score = clamp_1_5(round(
            1
            + 1.0 * has_direct_structural_evidence
            + 1.0 * has_direct_historical_evidence
            + 1.0 * citation_coverage
            + 0.5 * evidence_diversity
            + 0.5 * no_unsupported_claims
        ))
        """
        structural_types = {str(item.get("type", "")) for item in result.structural}
        historical_types = {str(item.get("type", "")) for item in result.historical}

        has_direct_structural = 1.0 if any(
            t in STRUCTURAL_TYPES for t in structural_types
        ) else 0.0

        has_direct_historical = 1.0 if any(
            t in (HISTORICAL_TYPES | {"commit", "pr", "review", "issue"})
            for t in historical_types
        ) else 0.0

        total_evidence = len(result.structural) + len(result.historical)
        citation_coverage = min(1.0, len(result.citations) / total_evidence) if total_evidence > 0 else 0.0

        families: set[str] = set()
        if result.structural:
            families.add("structural")
        for item in result.historical:
            t = str(item.get("type", ""))
            if t in {"commit", "pr", "review", "issue"}:
                families.add("source")
            elif t == "claim":
                families.add("claim")
        evidence_diversity = 1.0 if len(families) >= 2 else 0.0

        unsupported_keywords = {"unsupported", "dropped", "no evidence", "no historical"}
        has_unsupported = any(
            any(kw in w.lower() for kw in unsupported_keywords)
            for w in result.warnings
        )
        no_unsupported = 0.0 if has_unsupported else 1.0

        raw = (
            1.0
            + 1.0 * has_direct_structural
            + 1.0 * has_direct_historical
            + 1.0 * citation_coverage
            + 0.5 * evidence_diversity
            + 0.5 * no_unsupported
        )
        return max(1, min(5, round(raw)))
