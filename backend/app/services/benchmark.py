import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.graph.models import KnowledgeGraph
from backend.app.services.retrieval import RetrievalService

BENCHMARK_QUERIES = [
    "How does the agent pipeline execute a tool call?",
    "Why was progressive memory loading chosen?",
    "Is it safe to refactor ProviderAdapter?",
    "What should I inspect before reviewing changes touching ProviderAdapter?",
    "Create a cited context pack for an agent modifying the provider subsystem.",
]


class BenchmarkService:
    def __init__(self, graph: KnowledgeGraph, results_dir: Path | None = None) -> None:
        self.graph = graph
        self.results_dir = results_dir or Path(
            os.environ.get("DEVONBOARD_BENCHMARK_RESULTS_DIR", "./benchmark/results")
        )

    def run(self, repo: str, target_branch: str, target_commit: str | None = None) -> dict[str, object]:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
        retrieval = RetrievalService(self.graph)
        rows: list[dict[str, object]] = []
        for index, query in enumerate(BENCHMARK_QUERIES, start=1):
            result = retrieval.answer(query=query, mode="auto")
            rows.append(
                {
                    "query_id": index,
                    "query_text": query,
                    "mode": "devonboard",
                    "time_to_useful_answer_ms": result.retrieval_ms + result.synthesis_ms,
                    "citations_count": len(result.citations),
                    "evidence_count": len(result.structural) + len(result.historical),
                    "input_tokens": None,
                    "output_tokens": None,
                    "evidence_usefulness_score": self._score(result.citations, result.warnings),
                    "human_quality_score": None,
                }
            )
            rows.append(
                {
                    "query_id": index,
                    "query_text": query,
                    "mode": "plain_agent",
                    "time_to_useful_answer_ms": 0,
                    "citations_count": 0,
                    "evidence_count": 0,
                    "input_tokens": None,
                    "output_tokens": None,
                    "evidence_usefulness_score": 1,
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

    def _score(self, citations: list[dict[str, object]], warnings: list[str]) -> int:
        score = 1 + min(2, len(citations)) + (0 if warnings else 1)
        return max(1, min(5, score))
