import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.graph.models import KnowledgeGraph
from backend.app.services.retrieval import QueryResult, RetrievalService, STRUCTURAL_TYPES, HISTORICAL_TYPES

RESULT_QUERIES = [
    "Explain the backend architecture.",
    "How does the query endpoint process a user query?",
    "Why might query results be inaccurate?",
    "Which files are involved in vector indexing?",
    "Which functions synthesize the final answer?",
    "How does the scanner build the knowledge graph?",
    "What happens when Gemini is disabled?",
    "Which parts should be changed to improve retrieval quality?",
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
            
            # Extract metrics
            structural_types = {str(item.get("type", "")) for item in result.structural}
            historical_types = {str(item.get("type", "")) for item in result.historical}
            
            has_structural = len(result.structural) > 0
            has_historical = len(result.historical) > 0
            
            has_function_level = any(
                t in {"function", "class", "endpoint"} for t in structural_types
            )
            
            has_vector_hits = False
            if result.debug_info and "vector_hits" in result.debug_info:
                has_vector_hits = len(result.debug_info["vector_hits"]) > 0
                
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
            
            top_evidence_relevance = 0.0
            if result.debug_info and "ranked_nodes" in result.debug_info:
                ranked = result.debug_info["ranked_nodes"]
                if ranked:
                    top_evidence_relevance = ranked[0].get("score", 0.0)
                    
            citation_count = len(re.findall(r"\[(node|source):", result.answer))
            answer_specificity = min(1.0, (len(result.answer) / 1000.0) * 0.5 + (citation_count / 5.0) * 0.5)
            
            # Determine failures
            retrieval_failed = not (has_structural or has_historical)
            synthesis_failed = result.fallback_used or (not result.answer or "error" in result.answer.lower())
            
            if retrieval_failed and synthesis_failed:
                failure_type = "both_failed"
            elif retrieval_failed:
                failure_type = "retrieval_failure"
            elif synthesis_failed:
                failure_type = "synthesis_failure"
            else:
                failure_type = "none"

            rows.append(
                {
                    "query_id": index,
                    "query_text": query,
                    "time_to_useful_answer_ms": result.retrieval_ms + result.synthesis_ms,
                    "citations_count": len(result.citations),
                    "evidence_count": total_evidence,
                    "warnings_count": len(result.warnings),
                    "evidence_usefulness_score": self._evidence_usefulness_score(result),
                    "human_quality_score": None,
                    "metrics": {
                        "has_structural_evidence": has_structural,
                        "has_function_level_evidence": has_function_level,
                        "has_vector_hits": has_vector_hits,
                        "has_historical_evidence": has_historical,
                        "citation_coverage": citation_coverage,
                        "evidence_diversity": evidence_diversity,
                        "top_evidence_relevance": round(top_evidence_relevance, 4),
                        "fallback_used": result.fallback_used,
                        "llm_used": result.llm_used,
                        "answer_specificity": round(answer_specificity, 4),
                        "warning_count": len(result.warnings)
                    },
                    "failure_type": failure_type
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
