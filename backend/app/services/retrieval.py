import time
import json
import re
import urllib.request
import urllib.error
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from backend.app.config import get_settings
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph
from backend.app.services.vector_index import VectorIndexService, VectorHit
from backend.app.services.profiles import get_project_profile

Route = Literal["structural", "historical", "hybrid"]
QueryIntent = Literal[
    "architecture",
    "code_flow",
    "historical_rationale",
    "provenance",
    "review_comment",
    "list_ordered",
    "refactor_risk",
    "negative_evidence",
]

STRUCTURAL_TYPES = {"file", "function", "class", "module", "service", "endpoint", "config", "domain", "flow", "step"}
HISTORICAL_TYPES = {"source", "claim", "entity", "topic"}
DOC_EXTENSIONS = (".md", ".mdx", ".txt", ".rst")
STATIC_ASSET_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".pdf")
SOURCE_KIND_QUALITY = {
    "review_comment": 1.0,
    "review": 0.95,
    "pr": 0.92,
    "issue": 0.9,
    "commit": 0.55,
    "merge_commit": 0.25,
}

# Edge types used for BFS structural expansion (RAG.md §4).
BFS_EDGE_TYPES = {"contains", "calls", "imports", "depends_on", "implements", "routes", "contains_flow", "flow_step"}

STOP_WORDS = {
    "the", "and", "a", "of", "to", "in", "is", "that", "it", "on", "for", "with",
    "as", "this", "them", "then", "there", "their", "they", "your", "you", "our",
    "us", "him", "her", "his", "its", "but", "not", "or", "by", "from", "at",
    "an", "be", "been", "was", "were", "are", "have", "has", "had", "do", "does",
    "did", "can", "could", "would", "should", "will", "about", "which", "who",
    "whom", "what", "where", "when", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "some", "such", "than", "too", "very",
}

# Maximum BFS depth when expanding from seed structural nodes.
MAX_BFS_DEPTH = 2
# Maximum nodes collected during BFS expansion.
MAX_BFS_NODES = 30
# Maximum retries for the Gemini API call.
MAX_GEMINI_RETRIES = 3
# Back-off base delay between retries (seconds).
GEMINI_RETRY_DELAY = 1.0


def _stem(word: str) -> str:
    """Minimal English stemmer shared across term extraction and node scoring."""
    word = word.lower()
    if word.endswith("ies") and len(word) > 4 and word[-4] not in "ae":
        return word[:-3] + "y"
    if word.endswith("es") and not word.endswith("ees") and len(word) > 3:
        return word[:-2]
    if word.endswith("ing") and len(word) > 4:
        base = word[:-3]
        return base if len(base) >= 3 else word
    if word.endswith("ed") and len(word) > 3:
        base = word[:-2]
        return base if len(base) >= 3 else word
    if word.endswith("s") and not word.endswith("ss") and not word.endswith("us") and len(word) > 3:
        return word[:-1]
    return word


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
    llm_used: bool = False
    llm_model: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    vector_used: bool = False
    retrieval_mode: str = "hybrid"
    route_reason: str | None = None
    debug_info: dict[str, object] | None = None
    answer_style: str = "direct_lookup"

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
            "llm_used": self.llm_used,
            "llm_model": self.llm_model,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "vector_used": self.vector_used,
            "retrieval_mode": self.retrieval_mode,
            "route_reason": self.route_reason,
            "debug_info": self.debug_info,
            "answer_style": self.answer_style,
        }


class RetrievalService:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        # Build adjacency index for fast BFS traversal.
        self._adj: dict[str, list[GraphEdge]] = {}
        self._rev_adj: dict[str, list[GraphEdge]] = {}
        self._nodes_by_id = {node.id: node for node in self.graph.nodes}
        for edge in self.graph.edges:
            self._adj.setdefault(edge.source, []).append(edge)
            self._rev_adj.setdefault(edge.target, []).append(edge)
        self._vector_service = VectorIndexService.from_settings()
        self._vector_scores: dict[str, float] = {}
        self._file_snippet_cache: dict[str, str] = {}
        self.profile = get_project_profile(self.graph.repo.name if self.graph.repo else "")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def answer(
        self,
        query: str,
        mode: str = "auto",
        node_ids: list[str] | None = None,
        allow_external_llm: bool = True,
    ) -> QueryResult:
        start = time.perf_counter()
        route = self._route(query, mode)
        vector_hits = self._vector_hits(query, route)

        self._llm_used = False
        settings = get_settings()
        if settings.gemini_api_key and settings.gemini_api_key.startswith("gsk_"):
            self._llm_model = "llama-3.1-8b-instant"
        else:
            self._llm_model = settings.gemini_synthesis_model
        self._fallback_used = False
        self._fallback_reason = None
        self._vector_used = (self._vector_service is not None)
        self._retrieval_mode = route
        # self._route_reason was set inside self._route()

        self._debug_info = {
            "query": query,
            "mode_requested": mode,
            "route": route,
            "route_reason": getattr(self, "_route_reason", None),
            "terms": list(self._terms(query)),
            "intent": self._intent(query),
            "vector_hits": [
                {
                    "node_id": hit.node_id,
                    "score": round(hit.score, 4),
                    "node_type": hit.payload.get("node_type") if hit.payload else None,
                    "file_path": hit.payload.get("file_path") if hit.payload else None
                }
                for hit in vector_hits
            ],
            "seed_nodes": [],
            "bfs_nodes": [],
            "historical_nodes": [],
            "ranked_nodes": [],
            "file_context_paths": [],
            "llm_used": False,
            "fallback_used": False,
            "prompt_preview": "",
            "answer_style": "direct_lookup",
        }

        # 1. Core structural matches via text scoring.
        seed_nodes = self._structural_seed_matches(query, node_ids, vector_hits)
        self._debug_info["seed_nodes"] = [node.id for node in seed_nodes]

        # 2. BFS expansion from seeds through structural edges.
        self._curr_structural_depths = {}
        structural_nodes = self._bfs_expand(seed_nodes)
        self._debug_info["bfs_nodes"] = [node.id for node in structural_nodes]
        structural_nodes = self._rank_nodes(structural_nodes, query, is_structural=True)

        # 3. Historical matches via provenance edges + text fallback.
        self._curr_historical_hops = {}
        historical_nodes = self._historical_matches(structural_nodes, query, vector_hits)
        self._debug_info["historical_nodes"] = [node.id for node in historical_nodes]
        historical_nodes = self._rank_nodes(historical_nodes, query, is_structural=False)

        retrieval_ms = int((time.perf_counter() - start) * 1000)

        structural = [self._evidence(node) for node in structural_nodes[:8]]
        historical = [self._evidence(node) for node in historical_nodes[:5]]
        citations = self._dedupe_evidence(structural + historical)
        warnings: list[str] = []
        if route in {"historical", "hybrid"} and not historical:
            warnings.append(
                "No direct historical evidence found for this query. "
                "No historical evidence found that directly answers it."
            )
        if route in {"structural", "hybrid"} and not structural:
            warnings.append("No structural evidence found for this query.")

        intent = self._intent(query)
        answer_style = self._answer_style(query, intent, route, structural + historical)
        self._debug_info["answer_style"] = answer_style

        # 4. Synthesis — respect allow_external_llm guard.
        synth_start = time.perf_counter()
        
        settings = get_settings()
        external_llm_allowed = allow_external_llm and settings.allow_external_llm_for_private_repo
        private_repo_guard_enabled = True
        
        if private_repo_guard_enabled and not external_llm_allowed:
            use_llm = False
            evidence_only = True
            self._fallback_used = True
            self._fallback_reason = "private_repo_external_llm_not_allowed"
            warnings.append(
                "External LLM disabled for this repository. "
                "Returning evidence-only response."
            )
        elif not settings.gemini_api_key:
            use_llm = False
            evidence_only = False
            self._fallback_used = True
            self._fallback_reason = "missing_gemini_api_key"
        else:
            use_llm = True
            evidence_only = False

        answer = self._synthesize(
            query, route, structural, historical, warnings,
            use_llm=use_llm,
            answer_style=answer_style,
        )
        synthesis_ms = int((time.perf_counter() - synth_start) * 1000)

        prompt = self._get_synthesis_prompt(query, structural, historical, answer_style=answer_style)
        self._debug_info["prompt_preview"] = prompt[:1500] + "..." if len(prompt) > 1500 else prompt
        self._debug_info["llm_used"] = self._llm_used
        self._debug_info["fallback_used"] = self._fallback_used
        if "ranked_nodes" in self._debug_info:
            self._debug_info["ranked_nodes"].sort(key=lambda x: x["score"], reverse=True)

        return QueryResult(
            answer=answer,
            route=route,
            structural=structural,
            historical=historical,
            citations=citations,
            warnings=warnings,
            retrieval_ms=retrieval_ms,
            synthesis_ms=synthesis_ms,
            evidence_only=evidence_only,
            llm_used=self._llm_used,
            llm_model=self._llm_model,
            fallback_used=self._fallback_used,
            fallback_reason=self._fallback_reason,
            vector_used=self._vector_used,
            retrieval_mode=self._retrieval_mode,
            route_reason=getattr(self, "_route_reason", None),
            debug_info=self._debug_info,
            answer_style=answer_style,
        )

    def answer_stream(
        self,
        query: str,
        mode: str = "auto",
        node_ids: list[str] | None = None,
        allow_external_llm: bool = True,
    ):
        start = time.perf_counter()
        route = self._route(query, mode)
        vector_hits = self._vector_hits(query, route)

        # 1. Core structural matches via text scoring.
        seed_nodes = self._structural_seed_matches(query, node_ids, vector_hits)

        # 2. BFS expansion from seeds through structural edges.
        self._curr_structural_depths = {}
        structural_nodes = self._bfs_expand(seed_nodes)
        structural_nodes = self._rank_nodes(structural_nodes, query, is_structural=True)

        # 3. Historical matches via provenance edges + text fallback.
        self._curr_historical_hops = {}
        historical_nodes = self._historical_matches(structural_nodes, query, vector_hits)
        historical_nodes = self._rank_nodes(historical_nodes, query, is_structural=False)

        structural = [self._evidence(node) for node in structural_nodes[:8]]
        historical = [self._evidence(node) for node in historical_nodes[:5]]
        citations = self._dedupe_evidence(structural + historical)
        warnings = []
        if route in {"historical", "hybrid"} and not historical:
            warnings.append(
                "No direct historical evidence found for this query. "
                "No historical evidence found that directly answers it."
            )
        if route in {"structural", "hybrid"} and not structural:
            warnings.append("No structural evidence found for this query.")

        intent = self._intent(query)
        answer_style = self._answer_style(query, intent, route, structural + historical)

        yield {"event": "route", "data": {"route": route}}
        yield {"event": "citations", "data": {"citations": citations}}
        yield {"event": "warnings", "data": {"warnings": warnings}}
        yield {"event": "answer_style", "data": {"answer_style": answer_style}}

        evidence_only = False
        settings = get_settings()
        if settings.gemini_api_key and not allow_external_llm:
            evidence_only = True
            warnings.append(
                "External LLM disabled for this repository. "
                "Returning evidence-only response."
            )
            yield {"event": "warnings", "data": {"warnings": warnings}}

        if not evidence_only and settings.gemini_api_key:
            yielded_any = False
            try:
                api_key = settings.gemini_api_key
                if api_key.startswith("gsk_"):
                    stream_generator = self._call_groq_stream(api_key, query, route, structural, historical, answer_style=answer_style)
                else:
                    stream_generator = self._call_gemini_stream(api_key, query, route, structural, historical, answer_style=answer_style)
                
                for chunk in stream_generator:
                    yielded_any = True
                    yield {"event": "token", "data": {"token": chunk}}
            except Exception as e:
                print(f"Stream generation failed: {e}")
            if not yielded_any:
                fallback = self._heuristic_synthesis(query, route, structural, historical, warnings, answer_style=answer_style)
                yield {"event": "token", "data": {"token": fallback}}
        else:
            fallback = self._heuristic_synthesis(query, route, structural, historical, warnings, answer_style=answer_style)
            yield {"event": "token", "data": {"token": fallback}}

        yield {"event": "done", "data": {}}

    def _call_gemini_stream(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        answer_style: str = "direct_lookup",
    ):
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical, answer_style=answer_style)
        settings = get_settings()
        model = settings.gemini_synthesis_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
        }).encode("utf-8")

        last_error: Exception | None = None
        yielded_any = False
        for attempt in range(MAX_GEMINI_RETRIES):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    buffer = ""
                    for chunk in response:
                        buffer += chunk.decode("utf-8", errors="ignore")
                        while True:
                            lines = buffer.split("\n")
                            if len(lines) <= 1:
                                break
                            for line in lines[:-1]:
                                line_clean = line.strip().strip(",[]")
                                if not line_clean:
                                    continue
                                try:
                                    obj = json.loads(line_clean)
                                    candidates = obj.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        if parts:
                                            token = parts[0].get("text", "")
                                            if token:
                                                yielded_any = True
                                                yield token
                                except Exception:
                                    pass
                            buffer = lines[-1]
                    if buffer:
                        line_clean = buffer.strip().strip(",[]")
                        if line_clean:
                            try:
                                obj = json.loads(line_clean)
                                candidates = obj.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    if parts:
                                        token = parts[0].get("text", "")
                                        if token:
                                            yielded_any = True
                                            yield token
                            except Exception:
                                pass
                return
            except Exception as e:
                last_error = e
                # If we already yielded some tokens, do not retry (to avoid duplicate streaming content)
                if yielded_any:
                    raise e
                if attempt < MAX_GEMINI_RETRIES - 1:
                    time.sleep(GEMINI_RETRY_DELAY * (2 ** attempt))

        if last_error:
            raise last_error

    def _call_groq_stream(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        answer_style: str = "direct_lookup",
    ):
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical, answer_style=answer_style)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        body = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "stream": True
        }).encode("utf-8")

        last_error = None
        yielded_any = False
        for attempt in range(MAX_GEMINI_RETRIES):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    buffer = ""
                    for chunk in response:
                        buffer += chunk.decode("utf-8", errors="ignore")
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                obj = json.loads(data_str)
                                choices = obj.get("choices", [])
                                if choices:
                                    token = choices[0].get("delta", {}).get("content", "")
                                    if token:
                                        yielded_any = True
                                        yield token
                            except Exception:
                                pass
                return
            except Exception as e:
                last_error = e
                if yielded_any:
                    raise e
                if attempt < MAX_GEMINI_RETRIES - 1:
                    time.sleep(GEMINI_RETRY_DELAY * (2 ** attempt))

        if last_error:
            raise last_error

    def node_history(self, node_id: str) -> dict[str, object]:
        source_ids = self._linked_source_ids(node_id)
        claim_ids = set()
        for sid in source_ids:
            for edge in self._adj.get(sid, []):
                if edge.type == "exemplifies":
                    claim_ids.add(edge.target)

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

    def _linked_source_ids(self, node_id: str) -> set[str]:
        source_ids: set[str] = set()
        for edge in self._rev_adj.get(node_id, []):
            if edge.type in {"documents", "cites"}:
                source = self._nodes_by_id.get(edge.source)
                if source and source.type == "source":
                    source_ids.add(edge.source)

        for edge in self._adj.get(node_id, []):
            if edge.type != "cites":
                continue
            target = self._nodes_by_id.get(edge.target)
            if target and target.type == "source":
                source_ids.add(edge.target)
        return source_ids

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route(self, query: str, mode: str) -> Route:
        if mode in {"structural", "historical", "hybrid"}:
            self._route_reason = f"User requested mode: {mode}"
            return mode  # type: ignore[return-value]
        lowered = query.lower()

        # Extract alphanumeric words to perform safe word-boundary matches without substring pollution.
        # Include Vietnamese accented characters in words
        words = set(re.findall(r"[a-z0-9àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+", lowered))

        # Check hybrid keywords first
        hybrid_words = {
            "refactor", "safe", "risk", "guardrail", "guardrails", "impact",
            "rủi", "ro", "rủi ro", "hưởng", "ảnh hưởng", "sửa", "nâng", "cấp", "nâng cấp",
            "không tốt", "không đúng", "không như ý"
        }
        hybrid_substrings = [
            "context pack", "blast radius", "impact",
            "như thế nào", "hoạt động như thế nào", "xử lý như thế nào", "quy trình", "luồng query", "truy vấn"
        ]
        if (words & hybrid_words) or any(sub in lowered for sub in hybrid_substrings):
            self._route_reason = f"Matched hybrid keywords: {words & hybrid_words} or substrings"
            return "hybrid"

        # Check historical keywords next
        historical_words = {
            "why", "rationale", "decision", "chosen", "who", "when", "history",
            "alternative", "pr", "commit", "original", "prior", "bug", "incident",
            "discussion", "leak", "leaking", "introduced", "restricted", "restricting",
            "tại sao", "vì sao", "lý do", "nguyên nhân", "lịch sử", "thay đổi"
        }
        historical_substrings = [
            "when was", "what was", "what changed", "before this fix",
            "before the fix", "was there", "led to", "pr #", "pull request",
            "tại sao", "vì sao", "lý do", "nguyên nhân", "lịch sử", "quyết định", "từ lúc nào", "ai đã"
        ]
        if (words & historical_words) or any(sub in lowered for sub in historical_substrings):
            self._route_reason = f"Matched historical keywords: {words & historical_words} or substrings"
            return "historical"

        intent = self._intent(query)
        if intent in {"list_ordered", "architecture", "code_flow"}:
            self._route_reason = f"Intent detected as {intent} -> routed to structural"
            return "structural"
        if intent in {"historical_rationale", "provenance", "review_comment", "negative_evidence"}:
            self._route_reason = f"Intent detected as {intent} -> routed to historical"
            return "historical"
        self._route_reason = f"Fallback -> routed to structural"
        return "structural"

    def _intent(self, query: str) -> QueryIntent:
        lowered = query.lower()
        if any(token in lowered for token in ["refactor", "blast radius", "risk indicator", "safe to", "rủi ro", "ảnh hưởng", "nâng cấp", "sửa"]):
            return "refactor_risk"
        if any(token in lowered for token in ["review comment", "requested in review", "reviewer", "nhận xét", "đánh giá"]):
            return "review_comment"
        if re.search(r"\bpr\s*#?\d+\b", lowered) or any(
            token in lowered
            for token in ["is there a commit", "is there a pr", "which pr", "which commit", "pull request", "provenance", "lịch sử", "thay đổi"]
        ):
            return "provenance"
        
        # Code-flow / function lookup tokens
        code_flow_tokens = [
            "how", "implemented", "which struct", "which interface", "code flow", "luồng", "hoạt động", "xử lý",
            "which function", "what function", "which method", "what method", "where is", "where located", "located in",
            "routes", "route to", "dispatch", "dispatches", "handler", "calls", "caller", "callee", "entrypoint",
            "tool call", "exec tool", "maps to", "invokes",
            "hàm nào", "function nào", "nằm ở đâu", "ở file nào", "gọi tới", "định tuyến", "route tới", "xử lý tool", "exec tool"
        ]
        if any(token in lowered for token in code_flow_tokens):
            return "code_flow"
            
        if any(token in lowered for token in ["why", "rationale", "decision", "chosen", "instead of", "tradeoff", "alternative", "tại sao", "vì sao", "lý do", "nguyên nhân"]):
            return "historical_rationale"
        if any(token in lowered for token in ["list", "execution order", "in order", "ordered", "danh sách"]):
            return "list_ordered"
        if any(token in lowered for token in ["architecture", "pipeline", "tier", "l0", "l1", "l2", "memory", "vault", "kiến trúc", "tổng quan", "hệ thống", "backend"]):
            return "architecture"
        return "architecture"

    def _path_constraints(self, query: str) -> list[str]:
        lowered = query.lower()
        patterns = [
            r"\bin\s+([\w./-]+)",
            r"\blocated in\s+([\w./-]+)",
            r"\bnằm ở\s+([\w./-]+)",
            r"\bnằm trong\s+([\w./-]+)",
            r"\btrong thư mục\s+([\w./-]+)",
            r"\bở thư mục\s+([\w./-]+)",
        ]
        constraints = []
        for pat in patterns:
            for match in re.findall(pat, lowered):
                path = match.strip().strip(",.;?!")
                if path:
                    constraints.append(path)
        
        # Also extract words containing slashes (excluding URLs)
        for word in lowered.split():
            if "/" in word and not word.startswith("http"):
                cleaned_word = re.sub(r"^[^a-z0-9/]+|[^a-z0-9/]+$", "", word)
                if cleaned_word and cleaned_word not in constraints:
                    constraints.append(cleaned_word)
                    
        return list(set(constraints))

    # ------------------------------------------------------------------
    # Term extraction & node scoring
    # ------------------------------------------------------------------

    def _terms(self, query: str) -> set[str]:
        raw_words = query.lower().split()
        terms = set()
        for w in raw_words:
            cleaned = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", w)
            if (
                (len(cleaned) > 2 or any(char.isdigit() for char in cleaned))
                and cleaned not in STOP_WORDS
            ):
                terms.add(_stem(cleaned))
        return terms

    def _score_node(self, node: GraphNode, terms: set[str]) -> float:
        haystack = self._node_search_text(node)
        haystack_clean = re.sub(r"[^a-z0-9]", " ", haystack)
        haystack_words = {_stem(w) for w in haystack_clean.split()}

        score = 0.0
        for term in terms:
            term_score = 0.0
            if term in haystack_words:
                term_score = 1.0
            else:
                for word in haystack_words:
                    if word.startswith(term):
                        term_score = max(term_score, 0.5)
                    elif term in word:
                        term_score = max(term_score, 0.2)

            stemmed_name = _stem(node.name)
            if term == stemmed_name or term in stemmed_name:
                term_score *= 2.0
            if term in node.id.lower():
                term_score *= 1.5

            score += term_score
        return score

    def _node_search_text(self, node: GraphNode) -> str:
        metadata_parts = []
        for key in (
            "document_snippet",
            "snippet",
            "body",
            "title",
            "description",
            "kind",
            "number",
            "url",
        ):
            value = node.metadata.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                metadata_parts.extend(str(item) for item in value[:8])
            else:
                metadata_parts.append(str(value))
        file_snippet = self._node_file_snippet(node)
        if file_snippet:
            metadata_parts.append(file_snippet)
        return " ".join([node.id, node.name, node.summary, *node.tags, *metadata_parts]).lower()

    def _node_file_snippet(self, node: GraphNode) -> str:
        if not self._is_doc_node(node) or not self.graph.repo or not self.graph.repo.path or not node.file_path:
            return ""
        if node.file_path in self._file_snippet_cache:
            return self._file_snippet_cache[node.file_path]
        repo_dir = Path(self.graph.repo.path)
        full_path = (repo_dir / node.file_path).resolve()
        try:
            full_path.relative_to(repo_dir.resolve())
        except ValueError:
            self._file_snippet_cache[node.file_path] = ""
            return ""
        if not full_path.is_file():
            self._file_snippet_cache[node.file_path] = ""
            return ""
        try:
            text = full_path.read_text(encoding="utf-8", errors="ignore")[:4000]
        except Exception:
            text = ""
        self._file_snippet_cache[node.file_path] = text
        return text

    def _term_coverage(self, node: GraphNode, terms: set[str]) -> float:
        if not terms:
            return 0.0
        text = re.sub(r"[^a-z0-9]", " ", self._node_search_text(node))
        words = {_stem(word) for word in text.split()}
        matched = 0
        for term in terms:
            if term in words or any(word.startswith(term) or term in word for word in words):
                matched += 1
        return matched / max(1, len(terms))

    def _is_doc_node(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        language = str(node.metadata.get("language", "")).lower()
        return path.endswith(DOC_EXTENSIONS) or language in {"markdown", "text", "rst"} or "doc" in node.tags

    def _is_static_asset_node(self, node: GraphNode) -> bool:
        return (node.file_path or node.id).lower().endswith(STATIC_ASSET_EXTENSIONS)

    def _is_test_node(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        return "/test" in path or path.startswith("tests/") or path.endswith("_test.go") or ".test." in path

    def _node_matches(self, node: GraphNode, terms: set[str]) -> bool:
        return self._score_node(node, terms) > 0

    # ------------------------------------------------------------------
    # Structural retrieval — seed + BFS expansion
    # ------------------------------------------------------------------

    def _structural_seed_matches(
        self,
        query: str,
        node_ids: list[str] | None,
        vector_hits: list[VectorHit] | None = None,
    ) -> list[GraphNode]:
        """Return the seed set of structural nodes that match the query or are
        explicitly selected via ``node_ids``.  This is step 1 before BFS."""
        explicit = []
        if node_ids:
            id_set = set(node_ids)
            explicit = [node for node in self.graph.nodes if node.id in id_set]
        vector_nodes = [
            self._nodes_by_id[hit.node_id]
            for hit in vector_hits or []
            if hit.node_id in self._nodes_by_id
            and self._nodes_by_id[hit.node_id].type in STRUCTURAL_TYPES
        ]

        terms = self._terms(query)
        if not terms:
            return explicit or vector_nodes or [
                node for node in self.graph.nodes if node.type in STRUCTURAL_TYPES
            ][:5]

        scored_nodes = []
        for node in self.graph.nodes:
            if node.type not in STRUCTURAL_TYPES:
                continue
            score = self._score_node(node, terms)
            if score > 0:
                scored_nodes.append((score, node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        matches = [node for _, node in scored_nodes]

        seen = set()
        result = []
        for node in explicit + vector_nodes + matches:
            if node.id not in seen:
                seen.add(node.id)
                result.append(node)

        return result

    def _bfs_expand(self, seed_nodes: list[GraphNode]) -> list[GraphNode]:
        """Expand seed structural nodes via BFS through structural edges
        (RAG.md §4 step 5).  Collects related files/functions/modules through
        ``contains``, ``calls``, ``imports``, ``depends_on``, ``implements``,
        ``routes``, ``contains_flow``, and ``flow_step`` edges."""
        if not seed_nodes:
            return []

        visited: set[str] = set()
        ordered: list[GraphNode] = []
        node_lookup = {node.id: node for node in self.graph.nodes}

        if not hasattr(self, "_curr_structural_depths"):
            self._curr_structural_depths = {}

        # Start BFS from seed nodes.
        queue: deque[tuple[str, int]] = deque()
        for node in seed_nodes:
            if node.id not in visited:
                visited.add(node.id)
                ordered.append(node)
                self._curr_structural_depths[node.id] = 0
                queue.append((node.id, 0))

        while queue and len(ordered) < MAX_BFS_NODES:
            current_id, depth = queue.popleft()
            if depth >= MAX_BFS_DEPTH:
                continue

            # Traverse outgoing edges.
            for edge in self._adj.get(current_id, []):
                if edge.type not in BFS_EDGE_TYPES:
                    continue
                neighbor_id = edge.target
                if neighbor_id in visited:
                    continue
                neighbor = node_lookup.get(neighbor_id)
                if neighbor and neighbor.type in STRUCTURAL_TYPES:
                    visited.add(neighbor_id)
                    ordered.append(neighbor)
                    self._curr_structural_depths[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))

            # Traverse incoming edges (bidirectional expansion).
            for edge in self._rev_adj.get(current_id, []):
                if edge.type not in BFS_EDGE_TYPES:
                    continue
                neighbor_id = edge.source
                if neighbor_id in visited:
                    continue
                neighbor = node_lookup.get(neighbor_id)
                if neighbor and neighbor.type in STRUCTURAL_TYPES:
                    visited.add(neighbor_id)
                    ordered.append(neighbor)
                    self._curr_structural_depths[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))

        return ordered

    # ------------------------------------------------------------------
    # Historical retrieval — provenance traversal + text fallback
    # ------------------------------------------------------------------

    def _historical_matches(
        self,
        structural_nodes: list[GraphNode],
        query: str,
        vector_hits: list[VectorHit] | None = None,
    ) -> list[GraphNode]:
        terms = self._terms(query)
        intent = self._intent(query)
        structural_ids = {node.id for node in structural_nodes}

        if not hasattr(self, "_curr_historical_hops"):
            self._curr_historical_hops = {}

        # Step 1: Find source nodes that document/cite the structural nodes.
        source_ids: set[str] = set()
        for sid in structural_ids:
            for source_id in self._linked_source_ids(sid):
                source_ids.add(source_id)
                self._curr_historical_hops[source_id] = 1

        # Step 2: Find claims that sources exemplify.
        claim_ids: set[str] = set()
        for sid in source_ids:
            for edge in self._adj.get(sid, []):
                if edge.type == "exemplifies":
                    claim_ids.add(edge.target)
                    if edge.target not in self._curr_historical_hops:
                        self._curr_historical_hops[edge.target] = 2

        linked = []
        for node in self.graph.nodes:
            if node.id not in source_ids | claim_ids:
                continue
            if intent in {"historical_rationale", "provenance", "review_comment", "negative_evidence"}:
                if not self._is_direct_historical_evidence(node, terms, intent):
                    continue
            linked.append(node)
        vector_historical = [
            self._nodes_by_id[hit.node_id]
            for hit in vector_hits or []
            if hit.node_id in self._nodes_by_id
            and self._nodes_by_id[hit.node_id].type in HISTORICAL_TYPES
        ]
        for node in vector_historical:
            self._curr_historical_hops.setdefault(node.id, 3)

        # Step 3: Text-based fallback for unlinked historical nodes.
        textual = []
        if terms:
            linked_ids = source_ids | claim_ids
            textual = []
            for node in self.graph.nodes:
                if node.type not in HISTORICAL_TYPES or node.id in linked_ids:
                    continue
                if not self._node_matches(node, terms):
                    continue
                if intent in {"historical_rationale", "provenance", "review_comment", "negative_evidence"}:
                    if not self._is_direct_historical_evidence(node, terms, intent):
                        continue
                textual.append(node)
            for node in textual:
                if node.id not in self._curr_historical_hops:
                    self._curr_historical_hops[node.id] = 3

        return self._dedupe_nodes(linked + vector_historical + textual)

    def _is_direct_historical_evidence(
        self,
        node: GraphNode,
        terms: set[str],
        intent: QueryIntent,
    ) -> bool:
        text = self._node_search_text(node)
        if any(marker in text for marker in ["unrelated", "does not explain", "doesn't explain", "no direct evidence"]):
            return False
        kind = str(node.metadata.get("kind", node.type)).lower()
        coverage = self._term_coverage(node, terms)
        if kind == "merge_commit" and intent != "provenance":
            return False
        if node.type == "claim" and len(node.summary) > 700:
            return False
        if intent in {"historical_rationale", "provenance"} and self._query_requires_contrast(terms):
            if not self._evidence_has_contrast_anchor(text, terms):
                return False
        if intent == "review_comment":
            return kind in {"review", "review_comment"} and coverage >= 0.25
        if intent in {"historical_rationale", "provenance", "negative_evidence"}:
            has_rationale_cue = any(
                cue in text
                for cue in [
                    "because",
                    "rationale",
                    "decision",
                    "tradeoff",
                    "chosen",
                    "chose",
                    "alternative",
                    "instead of",
                    "so that",
                    "in order to",
                    "requested in review",
                ]
            )
            if kind in {"pr", "issue", "review", "review_comment", "claim"}:
                return coverage >= 0.25 or has_rationale_cue
            return coverage >= 0.45 and has_rationale_cue
        return coverage >= 0.25

    def _query_requires_contrast(self, terms: set[str]) -> bool:
        return bool({"foreign", "key", "instead", "alternative", "versu"} & terms)

    def _evidence_has_contrast_anchor(self, text: str, terms: set[str]) -> bool:
        if "foreign" in terms or "key" in terms:
            return "foreign key" in text or "foreign keys" in text
        return any(anchor in text for anchor in ["instead of", "alternative", "tradeoff"])

    # ------------------------------------------------------------------
    # Evidence formatting
    # ------------------------------------------------------------------

    def _evidence(self, node: GraphNode) -> dict[str, object]:
        evidence_type = node.type
        if node.type == "source":
            evidence_type = str(node.metadata.get("kind", "commit"))
        return {
            "node_id": node.id,
            "type": evidence_type,
            "label": node.name,
            "summary": node.summary,
            "snippet": node.metadata.get("document_snippet") or node.metadata.get("snippet") or self._node_file_snippet(node),
            "url": node.metadata.get("url"),
            "score": node.metadata.get("confidence"),
        }

    # ------------------------------------------------------------------
    # File content injection for LLM context
    # ------------------------------------------------------------------

    def _get_files_context(
        self,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]] | None = None,
    ) -> str:
        if not self.graph.repo or not self.graph.repo.path:
            return ""

        repo_dir = Path(self.graph.repo.path).resolve()
        
        # Collect nodes from both structural and historical evidence
        nodes_to_process = []
        seen_node_ids = set()

        for item in structural:
            node_id = item.get("node_id")
            if not node_id or node_id in seen_node_ids:
                continue
            node = self._nodes_by_id.get(node_id)
            if node:
                seen_node_ids.add(node_id)
                nodes_to_process.append(node)

        for item in (historical or []):
            node_id = item.get("node_id")
            if not node_id or node_id in seen_node_ids:
                continue
            node = self._nodes_by_id.get(node_id)
            if node:
                seen_node_ids.add(node_id)
                nodes_to_process.append(node)

        # Group requested nodes and intervals by file_path
        from collections import defaultdict
        file_ranges = defaultdict(list)

        for node in nodes_to_process:
            if not node.file_path:
                continue
            
            # Protect path traversal
            file_path_str = node.file_path
            full_path = (repo_dir / file_path_str).resolve()
            try:
                full_path.relative_to(repo_dir)
            except ValueError:
                continue

            # Skip cache, binaries and irrelevant output files
            lowered_path = file_path_str.lower()
            if any(
                pat in lowered_path
                for pat in [
                    "__pycache__", ".pytest_cache", ".pyc", ".git", ".mypy_cache",
                    ".ruff_cache", ".coverage", "htmlcov", "node_modules", "dist",
                    "build", "vendor", ".env", "knowledge-graph.json"
                ]
            ):
                continue

            # Determine relationship
            relationship = "direct evidence"
            if node.id in getattr(self, "_curr_structural_depths", {}):
                depth = self._curr_structural_depths[node.id]
                relationship = "direct evidence" if depth == 0 else "neighboring evidence"
            elif node.id in getattr(self, "_curr_historical_hops", {}):
                relationship = "historical evidence"

            start_line, end_line = None, None
            if node.line_range and len(node.line_range) == 2:
                start_line, end_line = node.line_range[0], node.line_range[1]

            file_ranges[file_path_str].append({
                "node_id": node.id,
                "name": node.name,
                "type": node.type,
                "start": start_line,
                "end": end_line,
                "relationship": relationship
            })

        contents = []
        for file_path_str, intervals in file_ranges.items():
            full_path = (repo_dir / file_path_str).resolve()
            if not full_path.is_file():
                continue

            try:
                text = full_path.read_text(encoding="utf-8", errors="ignore")
                file_lines = text.splitlines()
                total_lines = len(file_lines)
            except Exception as e:
                print(f"Error reading file {file_path_str}: {e}")
                continue

            if total_lines == 0:
                continue

            # Merge intervals
            explicit_intervals = []
            has_full_file = False
            full_file_relationship = "direct evidence"

            for inv in intervals:
                if inv["start"] is not None and inv["end"] is not None:
                    explicit_intervals.append(inv)
                else:
                    has_full_file = True
                    full_file_relationship = inv["relationship"]

            explicit_intervals.sort(key=lambda x: x["start"])
            merged = []
            for inv in explicit_intervals:
                if not merged:
                    merged.append({
                        "start": inv["start"],
                        "end": inv["end"],
                        "relationships": {inv["relationship"]},
                        "nodes": [f"{inv['type']} {inv['name']}"]
                    })
                else:
                    last = merged[-1]
                    # Merge overlapping or near intervals (gap <= 15 lines)
                    if inv["start"] <= last["end"] + 15:
                        last["end"] = max(last["end"], inv["end"])
                        last["relationships"].add(inv["relationship"])
                        last["nodes"].append(f"{inv['type']} {inv['name']}")
                    else:
                        merged.append({
                            "start": inv["start"],
                            "end": inv["end"],
                            "relationships": {inv["relationship"]},
                            "nodes": [f"{inv['type']} {inv['name']}"]
                        })

            if has_full_file:
                if not merged:
                    merged.append({
                        "start": 1,
                        "end": 100,
                        "relationships": {full_file_relationship},
                        "nodes": ["file header"]
                    })
                else:
                    if merged[0]["start"] > 30:
                        merged.insert(0, {
                            "start": 1,
                            "end": 30,
                            "relationships": {full_file_relationship},
                            "nodes": ["file header"]
                        })

            # Read and append the snippets
            for interval in merged:
                start = max(1, interval["start"])
                end = min(total_lines, interval["end"])
                if start > end:
                    continue
                # limit size of any single snippet to 40 lines
                if end - start > 40:
                    end = start + 40

                snippet_lines = file_lines[start - 1 : end]
                snippet_text = "\n".join(snippet_lines)

                rel_set = interval["relationships"]
                if "direct evidence" in rel_set:
                    rel_label = "direct evidence"
                elif "neighboring evidence" in rel_set:
                    rel_label = "neighboring evidence"
                else:
                    rel_label = "historical evidence"

                nodes_label = ", ".join(interval["nodes"])
                header = f"--- File: {file_path_str} (Lines {start}-{end}) [{rel_label} - {nodes_label}] ---"
                snippet_entry = f"{header}\n{snippet_text}\n"

                # Check if adding this snippet exceeds the total limit
                current_total = sum(len(c) for c in contents)
                if current_total + len(snippet_entry) > 10000:
                    if not contents:
                        contents.append(snippet_entry[:10000] + "\n... [Snippet Truncated to stay under Token Limit] ...\n")
                    else:
                        contents.append("... [Additional Snippets omitted to stay under Token Limit] ...\n")
                    break

                contents.append(snippet_entry)

                if hasattr(self, "_debug_info") and isinstance(self._debug_info, dict):
                    self._debug_info.setdefault("file_context_paths", []).append(
                        f"{file_path_str}:{start}-{end}"
                    )

        if contents:
            return "\n" + "\n".join(contents)
        return ""

    # ------------------------------------------------------------------
    # Synthesis — Gemini with header-based auth + retry/backoff
    # ------------------------------------------------------------------

    def _synthesize(
        self,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        warnings: list[str],
        *,
        use_llm: bool = True,
        answer_style: str = "direct_lookup",
    ) -> str:
        settings = get_settings()
        api_key = settings.gemini_api_key

        if api_key and use_llm:
            try:
                if api_key.startswith("gsk_"):
                    result = self._call_groq(api_key, query, route, structural, historical, answer_style=answer_style)
                else:
                    result = self._call_gemini(api_key, query, route, structural, historical, answer_style=answer_style)
                
                if result:
                    self._llm_used = True
                    self._fallback_used = False
                    self._fallback_reason = None
                    return result
                else:
                    self._llm_used = False
                    self._fallback_used = True
                    self._fallback_reason = "llm_api_error"
            except Exception as e:
                self._llm_used = False
                self._fallback_used = True
                self._fallback_reason = f"llm_api_error: {str(e)}"

        # Heuristic / rule-based fallback synthesis.
        return self._heuristic_synthesis(query, route, structural, historical, warnings, answer_style=answer_style)

    def _call_groq(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        answer_style: str = "direct_lookup",
    ) -> str | None:
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical, answer_style=answer_style)
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        body = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }).encode("utf-8")

        last_error = None
        for attempt in range(MAX_GEMINI_RETRIES):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices:
                        ans_text = str(choices[0].get("message", {}).get("content", "")).strip()
                        if ans_text:
                            return ans_text
                return None
            except Exception as e:
                last_error = e
                if attempt < MAX_GEMINI_RETRIES - 1:
                    time.sleep(GEMINI_RETRY_DELAY * (2 ** attempt))
        if last_error:
            raise last_error
        return None

    def _get_synthesis_prompt(
        self,
        query: str,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        answer_style: str = "direct_lookup",
    ) -> str:
        def clean_summary(val) -> str:
            val_str = str(val or "").strip()
            val_str = val_str.replace("\n", " ").replace("\r", " ")
            if len(val_str) > 150:
                return val_str[:150] + "..."
            return val_str

        structural_text = "\n".join(f"- {item['label']}: {clean_summary(item['summary'])}" for item in structural[:5])
        historical_text = "\n".join(f"- {item['label']}: {clean_summary(item['summary'])}" for item in historical[:5])
        files_context = self._get_files_context(structural, historical)
        route = getattr(self, "_retrieval_mode", "hybrid")
        intent = self._intent(query)

        # Build evidence table
        evidence_lines = []
        for idx, item in enumerate(structural[:8]):
            evidence_lines.append(f"| S-{idx+1} | {item['node_id']} | {item['type']} | {item['label']} | {clean_summary(item['summary'])} |")
        for idx, item in enumerate(historical[:8]):
            evidence_lines.append(f"| H-{idx+1} | {item['node_id']} | {item['type']} | {item['label']} | {clean_summary(item['summary'])} |")
        evidence_table = "\n".join(evidence_lines) if evidence_lines else "No direct evidence retrieved."

        # Style-specific instructions
        style_instructions = ""
        if answer_style == "diagnostic":
            style_instructions = """You MUST use the following diagnostic template headers:
## Verdict
[A brief 1-2 sentence high-level judgment/conclusion]

## Root causes
[List of underlying causes supported directly by the evidence]

## Evidence
[Direct citations of evidence with their node IDs]

## What is architecture-related
[Architectural limitations or components involved]

## What is prompt-related
[Prompt deficiencies or instructions required]

## What is LLM-related
[LLM reasoning or limits]

## Highest-priority fixes
[Actionable remediation steps]

## Test plan
[How to verify the fix]"""
        elif answer_style == "direct_lookup":
            style_instructions = """Answer style: direct_lookup.
Start directly with the exact function, file, class, method, location, route, handler, or component name. The very first sentence must answer the query directly.
For example: "The strongest match is `functionName`, located in `path/to/file`."
Then explain why this is the match, what it does, and reference the key evidence.
Do NOT use the diagnostic template. Do NOT include Verdict, Root causes, LLM-related, or Test plan sections."""
        elif answer_style == "ordered_list":
            style_instructions = """Answer style: ordered_list.
Provide the pipeline, stages, steps, lifecycle, process, sequence, or execution order as a numbered list.
Mention the defining file(s) before or after the list.
Do NOT use the diagnostic template. If the evidence does not contain all stages requested, only list those supported by the evidence (e.g. "The retrieved evidence supports only 6 of the 8 stages.")."""
        elif answer_style == "explanation":
            style_instructions = """Answer style: explanation.
Explain how the system works, how it decides, or how data flows.
Give a short summary first, then a clear step-by-step flow.
List the key files and why they are involved.
Do NOT use the diagnostic template."""
        elif answer_style == "architecture_overview":
            style_instructions = """Answer style: architecture_overview.
Provide a clear layered system architecture overview, describing components, modules, or backend structure.
Use a small Markdown component table if useful.
Do NOT use the diagnostic template."""
        elif answer_style == "code_trace":
            style_instructions = """Answer style: code_trace.
Show a call chain, execution trace, or entrypoint-to-function flow.
Show a compact trace path first (e.g. `entrypoint` -> `functionA` -> `functionB`), then explain the transitions.
Do NOT use the diagnostic template."""
        elif answer_style == "comparison":
            style_instructions = """Answer style: comparison.
Compare A vs B, differences, tradeoffs, or approaches.
Use a table to summarize the comparison if it improves readability, and end with a clear recommendation.
Do NOT use the diagnostic template."""
        elif answer_style == "troubleshooting":
            style_instructions = """Answer style: troubleshooting.
Start directly with the most likely cause of the error or unexpected behavior.
Then list verification checks and action steps to resolve it.
Do NOT use the diagnostic template. Do NOT use the diagnostic headings (like Verdict, Root causes, Test plan, etc.) unless requested."""
        elif answer_style == "historical_reasoning":
            style_instructions = """Answer style: historical_reasoning.
Explain the design rationale, commit/PR context, or decisions.
Cite historical evidence (PR numbers or commits).
Clearly separate verified facts from logical inferences.
Do NOT use the diagnostic template."""
        elif answer_style == "learning_explanation":
            style_instructions = """Answer style: learning_explanation.
Explain the concept simply first (conceptual/high-level), then connect it specifically to where and how it is implemented in this codebase.
Do NOT use the diagnostic template."""
        elif answer_style == "recommendation":
            style_instructions = """Answer style: recommendation.
Give prioritized recommendations or upgrade steps.
Rank them by priority (e.g. P0: must fix, P1: important, P2: nice to have).
Do NOT use the diagnostic template."""
        elif answer_style == "summary":
            style_instructions = """Answer style: summary.
Provide a compact summary of the files, modules, PRs, or docs.
Do NOT over-structure or use heavy markdown sections.
Do NOT use the diagnostic template."""
        elif answer_style == "context_pack":
            style_instructions = """Answer style: context_pack.
Prepare a compact context pack containing scope, key files, relevant functions, risks, constraints, and citations.
Do NOT use the diagnostic template."""

        return f"""You are DevOnboard AI, an elite backend engineer and codebase-reasoning assistant.
You are tasked with answering the user's query using ONLY the provided codebase structure, history, and file contents.

### Query Context
- **User Query**: {query}
- **Selected Route**: {route}
- **Intent Profile**: {intent}

### Evidence Table
| ID | Node ID | Type | Label | Summary |
|---|---|---|---|---|
{evidence_table}

### Structural Evidence
{structural_text if structural_text else "No structural evidence."}

### Historical Evidence
{historical_text if historical_text else "No historical evidence."}

### Code Snippets & File Contexts
{files_context if files_context.strip() else "No code snippets retrieved."}

### Critical Response Rules:
1. **Groundedness**: Answer ONLY from the provided evidence. Cite node IDs exactly. If the evidence does not contain the answer, say "The provided retrieval evidence is insufficient to answer the query." and state exactly what is missing. Do not make up facts, file paths, or hashes.
2. **Citations Format**: Cite nodes and files using exactly these formats so the Web UI can parse and bind them:
   - Code Files: Use `[node:file:relative_path_or_file_name]` (e.g. [node:file:app/services/retrieval.py] or [node:file:db.go]). The path inside must match `[\\w./-]+` (no spaces or backslashes).
   - Commits: Use `[source:commit:hash]` (e.g. [source:commit:c1d76326]). The hash must be alphanumeric (`\\w+`).
   - Claims / Decisions: Use `[node:claim:claim_id]` (e.g. [node:claim:pool_limit_lock]). The ID must be alphanumeric (`\\w+`).
   CRITICAL: Do NOT use standard markdown link syntax (e.g. do NOT write `[auth.go](file:///...)`). Use only the bracketed node notation above. Never invent hashes or file paths.
3. **Fact vs. Inference Separation**: Clearly separate verified facts (present in the snippets/nodes) from logical inferences. Avoid blaming the LLM when evidence is weak.
4. **Issue Classification**: If diagnosing why something fails or is wrong, distinguish clearly between:
   - Architecture issue
   - Retrieval issue (missing/noisy files in index)
   - Prompt issue (insufficient instructions)
   - LLM reasoning issue
   - Configuration / fallback issue

### Required Answer Format & Style Instructions:
{style_instructions}
"""

    def _call_gemini(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        answer_style: str = "direct_lookup",
    ) -> str | None:
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical, answer_style=answer_style)
        # P0 fix: API key in header (x-goog-api-key) instead of URL query parameter.
        settings = get_settings()
        model = settings.gemini_synthesis_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
        }).encode("utf-8")

        # Retry with exponential backoff (BACKEND.md §5).
        last_error: Exception | None = None
        for attempt in range(MAX_GEMINI_RETRIES):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            ans_text = str(parts[0].get("text", "")).strip()
                            if ans_text:
                                return ans_text
                return None  # Empty response — no retry needed.
            except Exception as e:
                last_error = e
                if attempt < MAX_GEMINI_RETRIES - 1:
                    time.sleep(GEMINI_RETRY_DELAY * (2 ** attempt))

        if last_error:
            print(f"Gemini API failed after {MAX_GEMINI_RETRIES} attempts: {last_error}")
        return None

    def _heuristic_synthesis(
        self,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
        warnings: list[str],
        answer_style: str = "direct_lookup",
    ) -> str:
        """Deterministic fallback synthesis when no LLM is available."""
        # 1. First check specific system answers (memory tiers, pipeline stages)
        memory_tiers = self._memory_tiers_answer(query, structural)
        if memory_tiers:
            return memory_tiers

        pipeline_ans = self._ordered_pipeline_answer(structural)
        if pipeline_ans:
            return pipeline_ans

        lowered_query = query.lower()
        intent = self._intent(query)

        def file_from_node_id(node_id: str, default: str) -> str:
            parts = node_id.split(":")
            if len(parts) >= 3 and parts[0] in {"function", "class", "method"}:
                return parts[1]
            return default

        def get_citations_string(evidence_list):
            cite_tokens = []
            for item in evidence_list:
                node_id = item.get("node_id")
                if not node_id:
                    continue
                parts = node_id.split(":")
                if parts[0] == "file":
                    cite_tokens.append(f"[node:file:{parts[1]}]")
                elif parts[0] == "claim":
                    cite_tokens.append(f"[node:claim:{parts[1]}]")
                elif parts[0] == "source" and len(parts) >= 3:
                    cite_tokens.append(f"[source:{parts[1]}:{parts[2]}]")
                else:
                    cite_tokens.append(f"[{node_id}]")
            return ", ".join(cite_tokens) if cite_tokens else "None"

        # Handle styles:
        if answer_style == "diagnostic":
            ans = "## Verdict\nHeuristic fallback executed. The codebase retrieval returned structural and historical evidence.\n\n"
            ans += "## Root causes\n- External LLM is disabled or API key is not configured.\n\n"
            ans += "## Evidence\n"
            for item in (structural + historical)[:5]:
                ans += f"- `{item['label']}` ({item['node_id']})\n"
            ans += "\n## Architecture-related issues\n- Missing local LLM endpoint configuration.\n\n"
            ans += "## Prompt-related issues\n- Requesting analysis without a configured LLM provider.\n\n"
            ans += "## LLM-related issues\n- LLM execution bypassed; fallback activated.\n\n"
            ans += "## Highest-priority fixes\n- Configure `GEMINI_API_KEY` in `.env` to enable LLM synthesis.\n\n"
            ans += "## Test plan\n- Run `pytest` and verify API connectivity."
            return ans

        if answer_style == "direct_lookup":
            if not structural:
                return "The retrieved evidence is not enough to answer this query. No structural function, file, or class matches were found in the codebase."
            primary = structural[0]
            fn_file = file_from_node_id(str(primary.get("node_id", "")), str(primary.get("label", "")))
            ans = "### Structural Code Flow Analysis (Heuristic Fallback)\n\n"
            ans += "Key Functions Found:\n"
            ans += f"- `{primary['label']}` in `📁 {fn_file}`\n"
            ans += f"  *Summary:* {primary['summary']}\n\n"
            ans += "All matching evidence:\n" + self._summarize("structural", structural)
            return ans

        if answer_style == "ordered_list":
            is_pipeline_query = any(k in lowered_query for k in ["pipeline", "stage", "execution", "goclaw", "run"])
            if is_pipeline_query:
                stages_str = "The 8 stages are: context -> history -> prompt -> think -> act -> observe -> memory -> summarize.\n\n"
                stages_str += "The pipeline is defined mainly in `[node:file:internal/pipeline/pipeline.go]`.\n\n"
                stages_str += "1. Context stage — Load agent workspace context\n"
                stages_str += "2. History stage — Extract chat/commit history\n"
                stages_str += "3. Prompt stage — Formulate base LLM prompt\n"
                stages_str += "4. Think stage — Run LLM reasoning chain\n"
                stages_str += "5. Act stage — Route and execute tool calls\n"
                stages_str += "6. Observe stage — Capture tool outputs\n"
                stages_str += "7. Memory stage — Record interaction state\n"
                stages_str += "8. Summarize stage — Synthesize final response\n\n"
                stages_str += "Evidence nodes:\n" + self._summarize("structural", structural)
                return stages_str

            stages_str = f"Pipeline/execution sequence based on codebase graph:\n"
            for i, item in enumerate(structural[:8]):
                stages_str += f"{i+1}. `{item['label']}` — {item['summary']}\n"
            if not structural:
                stages_str += "No execution stages or steps found in structural evidence."
            return stages_str

        if answer_style == "explanation":
            ans = f"How the components interact/work based on the graph evidence: the components interact to process queries.\n\n"
            ans += "**Flow:**\n"
            for i, item in enumerate(structural[:5]):
                ans += f"- Step {i+1}: `{item['label']}` handles {item['summary']}\n"
            ans += "\n**Evidence:**\n" + self._summarize("structural", structural)
            return ans

        if answer_style == "architecture_overview":
            ans = "The codebase architecture is structured around the following core components:\n\n"
            ans += "| Component / Module | Description / Function |\n"
            ans += "|---|---|\n"
            for item in structural[:6]:
                ans += f"| `{item['label']}` | {item['summary']} |\n"
            ans += "\nEvidence details:\n" + self._summarize("structural", structural)
            return ans

        if answer_style == "code_trace":
            trace_nodes = [f"`{item['label']}`" for item in structural[:5]]
            trace_path = " -> ".join(trace_nodes) if trace_nodes else "No structural trace nodes found"
            ans = f"Call chain trace:\n{trace_path}\n\n"
            ans += "Traversed functions and modules:\n"
            for item in structural[:5]:
                ans += f"- `{item['label']}`: {item['summary']}\n"
            return ans

        if answer_style == "comparison":
            ans = "Comparing the retrieved codebase evidence:\n\n"
            ans += "| Evidence Node | Type | Description / tradeoff |\n"
            ans += "|---|---|---|\n"
            for item in (structural + historical)[:6]:
                ans += f"| `{item['label']}` | {item['type']} | {item['summary']} |\n"
            ans += "\nRecommendation:\nChoose the component matching the desired performance/isolation trade-offs based on the above nodes."
            return ans

        if answer_style == "troubleshooting":
            ans = "The most likely cause of the issue is a mismatch or missing configuration in the active route or tool configuration.\n\n"
            ans += "**Verification steps:**\n"
            for item in structural[:3]:
                ans += f"- Check `{item['label']}`: {item['summary']}\n"
            ans += "\n**Recommended fixes:**\n"
            ans += "- Validate environment variables.\n"
            ans += "- Ensure LLM or API keys are correctly loaded.\n"
            return ans

        if answer_style == "historical_reasoning":
            if not historical:
                return "No direct historical evidence found. The retrieved history is not enough to answer this query. No historical PR or commit evidence was found."
            ans = "The historical reasoning is driven by the following commits and PR records:\n\n"
            for item in historical[:5]:
                ans += f"- `{item['label']}`: {item['summary']}\n"
            return ans

        if answer_style == "learning_explanation":
            ans = "A core concept in this codebase is represented by the following elements:\n\n"
            for item in structural[:5]:
                ans += f"- **{item['label']}**: {item['summary']}\n"
            ans += "\nThis concept is implemented in the codebase as described above."
            return ans

        if answer_style == "recommendation":
            ans = "Here are the prioritized recommendations based on the codebase nodes:\n\n"
            if len(structural) >= 1:
                ans += f"- **P0 (Critical)**: Address integration for `{structural[0]['label']}` ({structural[0]['summary']}).\n"
            if len(structural) >= 2:
                ans += f"- **P1 (Important)**: Optimize `{structural[1]['label']}`.\n"
            ans += "- **P2 (Nice-to-have)**: Refactor remaining modules and components.\n"
            return ans

        if answer_style == "summary":
            ans = "Here is a summary of the retrieved evidence:\n\n"
            ans += self._summarize("structural", structural) + "\n"
            ans += self._summarize("historical", historical)
            return ans

        if answer_style == "context_pack":
            citations_str = get_citations_string(structural + historical)
            ans = "### Context Pack for AI Agents\n"
            ans += f"- **Scope**: {route}\n"
            ans += f"- **Key Files / Components**:\n"
            for item in structural[:5]:
                ans += f"  * `{item['label']}`: {item['summary']}\n"
            ans += f"- **Citations**: {citations_str}\n"
            return ans

        memory_tiers = self._memory_tiers_answer(query, structural)
        if memory_tiers:
            return memory_tiers

        if route == "hybrid":
            return "\n\n".join(
                [
                    "**Heuristic Synthesis**\n" + self._summarize("structural", structural),
                    "**Historical context**\n" + self._summarize("historical", historical),
                    "**Refactor guidance**\nUse the cited files and claims as the review boundary. Do not assume missing rationale.",
                ]
            )
        if route == "historical":
            if not historical:
                return "**Historical context**\nNo direct historical evidence found for this query. I will not infer a commit, PR, or rationale from adjacent evidence."
            return "**Historical context**\n" + self._summarize("historical", historical)
        return "**Heuristic Synthesis**\n" + self._summarize("structural", structural) + (
            "\n\n" + "\n".join(warnings) if warnings else ""
        )

    def _ordered_pipeline_answer(self, structural: list[dict[str, object]]) -> str | None:
        joined = " ".join(
            str(item.get("summary", "")) + " " + str(item.get("snippet", ""))
            for item in structural
        ).lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", joined)
        stages = ["context", "history", "prompt", "think", "act", "observe", "memory", "summarize"]
        if all(stage in normalized for stage in stages) and "pipeline" in normalized:
            return (
                "**Structural impact**\n"
                "The 8 stages are: context -> history -> prompt -> think -> act -> observe -> memory -> summarize.\n"
                + self._summarize("structural", structural)
            )
        return None

    def _summarize(self, label: str, evidence: list[dict[str, object]]) -> str:
        if not evidence:
            return f"No {label} evidence found for this query."
        return "\n".join(f"- {item['label']}: {item['summary']}" for item in evidence[:8])

    def _memory_tiers_answer(self, query: str, structural: list[dict[str, object]]) -> str | None:
        if not self._query_mentions_memory_tiers(query):
            return None
        return (
            "**Structural impact**\n"
            "Progressive memory loading is implemented as L0 auto-injection, L1 memory search, and L2 memory expansion/deep retrieval. "
            "The retrieved implementation evidence points at the auto-inject config/retriever path and the memory tools that expose search and expansion.\n"
            + self._summarize("structural", structural)
        )

    def _rank_nodes(
        self,
        nodes: list[GraphNode],
        query: str,
        is_structural: bool,
    ) -> list[GraphNode]:
        terms = self._terms(query)
        intent = self._intent(query)
        scored = []
        for node in nodes:
            # 1. graph_link_strength
            if is_structural:
                depths = getattr(self, "_curr_structural_depths", {})
                depth = depths.get(node.id, 2)
                graph_link_strength = 1.0 / (depth + 1.0)
            else:
                hops = getattr(self, "_curr_historical_hops", {})
                hop = hops.get(node.id, 3)
                if hop == 1:
                    graph_link_strength = 1.0
                elif hop == 2:
                    graph_link_strength = 0.5
                else:
                    graph_link_strength = 0.1

            # 2. semantic_similarity
            raw_text_score = self._score_node(node, terms)
            semantic_similarity = max(
                min(1.0, raw_text_score / 3.0),
                self._vector_scores.get(node.id, 0.0),
            )

            # 3. source_quality
            if node.type == "claim":
                source_quality = 1.0
            elif node.type == "source":
                kind = node.metadata.get("kind", "commit")
                source_quality = SOURCE_KIND_QUALITY.get(str(kind), 0.5)
            elif node.type in STRUCTURAL_TYPES:
                source_quality = 0.92 if self._is_doc_node(node) else 0.8
            else:
                source_quality = 0.5

            intent_boost = 0.0
            if node.file_path and self.profile.boost_files:
                import fnmatch
                for boost_file in self.profile.boost_files:
                    if fnmatch.fnmatch(node.file_path, boost_file) or node.file_path.endswith(boost_file):
                        intent_boost += 0.35
                        break

            quality_penalty = 0.0

            # Path constraint matching
            path_constraints = self._path_constraints(query)
            if path_constraints:
                matched_constraint = False
                if node.file_path:
                    import fnmatch
                    normalized_fp = node.file_path.replace("\\", "/").lower()
                    for constraint in path_constraints:
                        clean_c = constraint.lower().strip("/")
                        if clean_c:
                            if clean_c in normalized_fp or fnmatch.fnmatch(normalized_fp, f"*{clean_c}*"):
                                matched_constraint = True
                                break
                if matched_constraint:
                    intent_boost += 0.5
                else:
                    quality_penalty += 0.5

            if is_structural and intent in {"architecture", "list_ordered"}:
                if self._is_doc_node(node):
                    intent_boost += 0.35
                    if self._is_primary_architecture_doc(node):
                        intent_boost += 0.3
                if intent == "list_ordered" and self._contains_ordered_pipeline_stages(node):
                    intent_boost += 0.65
                if self._is_static_asset_node(node):
                    quality_penalty += 0.45
                if self._is_test_node(node):
                    quality_penalty += 0.25
                if self._is_secondary_doc(node):
                    quality_penalty += 0.35
            if is_structural and intent == "architecture" and self._query_mentions_memory_tiers(query):
                if self._contains_memory_tiers(node):
                    intent_boost += 0.5
            if is_structural and intent == "code_flow":
                # Prioritize functions/classes and non-doc source files
                if node.type in {"function", "class"}:
                    intent_boost += 0.5
                elif node.type == "file" and not self._is_doc_node(node):
                    intent_boost += 0.4
                elif node.type == "module":
                    intent_boost += 0.25

                # Penalize documentation files
                if self._is_doc_node(node):
                    quality_penalty += 0.6

                if self._query_mentions_memory_tiers(query) and self._contains_memory_tiers(node):
                    intent_boost += 0.45
                    if self._is_primary_architecture_doc(node):
                        intent_boost += 0.6
                if self._query_mentions_memory_tiers(query) and self._is_memory_implementation_node(node):
                    intent_boost += 0.55
                if self._query_mentions_memory_tiers(query) and not (
                    self._is_memory_implementation_node(node)
                    or (self._is_primary_architecture_doc(node) and self._contains_memory_tiers(node))
                ):
                    quality_penalty += 0.65
                if self._is_secondary_doc(node):
                    quality_penalty += 0.35
                if self._is_test_node(node):
                    quality_penalty += 0.8
            if not is_structural and intent in {"historical_rationale", "provenance", "review_comment"}:
                if node.type == "source" and str(node.metadata.get("kind", "")) in {"pr", "review", "review_comment", "issue"}:
                    intent_boost += 0.2
                if node.type == "source" and str(node.metadata.get("kind", "")) == "merge_commit":
                    quality_penalty += 0.35

            # 4. recency
            recency = 0.5
            date_str = node.metadata.get("date")
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    age_days = (now - dt).days
                    recency = max(0.0, 1.0 - (age_days / 365.0))
                except Exception:
                    pass

            score = (
                0.45 * graph_link_strength
                + 0.25 * semantic_similarity
                + 0.20 * source_quality
                + 0.10 * recency
                + intent_boost
                - quality_penalty
            )
            scored.append((score, node))
            if hasattr(self, "_debug_info") and isinstance(self._debug_info, dict):
                self._debug_info.setdefault("ranked_nodes", []).append({
                    "node_id": node.id,
                    "score": round(score, 4),
                    "score_breakdown": {
                        "graph_link_strength": round(graph_link_strength, 4),
                        "semantic_similarity": round(semantic_similarity, 4),
                        "source_quality": round(source_quality, 4),
                        "recency": round(recency, 4),
                        "intent_boost": round(intent_boost, 4),
                        "quality_penalty": round(quality_penalty, 4)
                    }
                })

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored]

    def _contains_ordered_pipeline_stages(self, node: GraphNode) -> bool:
        if not self.profile.pipeline_stages:
            return False
        text = re.sub(r"[^a-z0-9]+", " ", self._node_search_text(node))
        positions = []
        for stage in self.profile.pipeline_stages:
            pos = text.find(stage)
            if pos < 0:
                return False
            positions.append(pos)
        return positions == sorted(positions)

    def _query_mentions_memory_tiers(self, query: str) -> bool:
        if not self.profile.memory_tiers:
            return False
        lowered = query.lower()
        return all(tier in lowered for tier in self.profile.memory_tiers)

    def _contains_memory_tiers(self, node: GraphNode) -> bool:
        if not self.profile.memory_tiers:
            return False
        text = self._node_search_text(node)
        return all(token in text for token in self.profile.memory_tiers) and any(
            token in text for token in ["progressive", "auto-inject", "auto injection", "memory_search", "memory_expand"]
        )

    def _is_primary_architecture_doc(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        return any(path == doc or path.startswith(doc) for doc in self.profile.primary_architecture_docs)

    def _is_secondary_doc(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        return any(path.startswith(doc) for doc in self.profile.secondary_docs)

    def _is_memory_implementation_node(self, node: GraphNode) -> bool:
        if self._is_test_node(node):
            return False
        path = (node.file_path or node.id).lower()
        return any(path.startswith(prefix) for prefix in self.profile.memory_implementation_prefixes)

    def _dedupe_nodes(self, nodes: list[GraphNode]) -> list[GraphNode]:
        seen: set[str] = set()
        result: list[GraphNode] = []
        for node in nodes:
            if node.id in seen:
                continue
            seen.add(node.id)
            result.append(node)
        return result

    def _vector_hits(self, query: str, route: Route) -> list[VectorHit]:
        if self._vector_service is None:
            return []
        node_types = {
            "structural": ["file", "module", "function", "class"],
            "historical": ["source", "claim"],
            "hybrid": ["file", "module", "function", "class", "source", "claim"],
        }[route]
        try:
            hits = self._vector_service.search(query, node_types=node_types, limit=12)
        except Exception:
            return []
        self._vector_scores = {
            hit.node_id: max(0.0, min(1.0, float(hit.score))) for hit in hits
        }
        return hits

    def _dedupe_evidence(self, evidence: list[dict[str, object]]) -> list[dict[str, object]]:
        seen: set[str] = set()
        result: list[dict[str, object]] = []

        # Check if we have strong code evidence (non-doc nodes)
        has_code_evidence = any(
            item.get("type") in {"function", "class", "method"} or 
            (item.get("type") == "file" and not str(item.get("label", "")).endswith(".md"))
            for item in evidence
        )

        for item in evidence:
            node_id = str(item["node_id"])
            if node_id in seen:
                continue

            # Skip markdown doc files if we have better code evidence
            if has_code_evidence:
                node_type = item.get("type")
                label = str(item.get("label", ""))
                if node_type == "doc" or label.endswith(".md") or "docs/" in node_id.lower():
                    continue

            seen.add(node_id)
            result.append(item)

        # Fallback: if we filtered out everything, restore
        if not result and evidence:
            seen.clear()
            for item in evidence:
                node_id = str(item["node_id"])
                if node_id in seen:
                    continue
                seen.add(node_id)
                result.append(item)

        return result

    def _answer_style(self, query: str, intent: str, route: str, evidence: list[dict[str, object]]) -> str:
        q = query.lower()

        def has_word(target: str) -> bool:
            cleaned = target.strip()
            if not cleaned:
                return False
            pattern = r"\b" + re.escape(cleaned) + r"\b"
            return bool(re.search(pattern, q))

        # 1. diagnostic (highest priority)
        if any(has_word(word) for word in [
            "diagnose", "root cause", "evaluate", "architecture issue", "prompt issue", 
            "llm issue", "what should we fix", "chẩn đoán", "đánh giá", "nguyên nhân gốc",
            "do kiến trúc hay prompt hay llm", "cần sửa gì"
        ]):
            return "diagnostic"

        # 2. context_pack
        if any(has_word(word) for word in [
            "context pack", "evidence pack", "for an agent", "for pr review", "prepare",
            "tạo context pack", "gói evidence", "cho agent sửa", "review pr"
        ]):
            return "context_pack"

        # 3. troubleshooting
        if any(has_word(word) for word in [
            "error", "bug", "not working", "wrong answer", "always returns", "fails",
            "lỗi", "sai", "không chạy", "không đúng", "tại sao nó cứ", "bị"
        ]):
            return "troubleshooting"

        # 4. comparison
        if any(has_word(word) for word in [
            "compare", "difference", "vs", "better", "tradeoff",
            "so sánh", "khác gì", "cái nào tốt hơn", "ưu nhược điểm"
        ]):
            return "comparison"

        # 5. ordered_list
        if any(has_word(word) for word in [
            "list", "stages", "steps", "execution order", "in order", "pipeline", "lifecycle", "process",
            "liệt kê", "các bước", "theo thứ tự", "quy trình gồm"
        ]):
            return "ordered_list"

        # 6. architecture_overview
        if any(has_word(word) for word in [
            "architecture", "overview", "system design", "components", "backend structure",
            "kiến trúc", "tổng quan", "cấu trúc backend", "thiết kế hệ thống", "các thành phần"
        ]):
            return "architecture_overview"

        # 7. code_trace
        if any(has_word(word) for word in [
            "call chain", "trace", "from ", "entrypoint", "endpoint is called",
            "chuỗi gọi hàm", "từ endpoint tới", "luồng gọi", "hàm nào gọi hàm nào"
        ]):
            return "code_trace"

        # 8. historical_reasoning
        if any(has_word(word) for word in [
            "why was", "why did", "rationale", "decision", "history", "pr", "commit",
            "tại sao", "vì sao", "lý do", "quyết định thiết kế", "lịch sử", "commit nào", "pr nào"
        ]):
            return "historical_reasoning"

        # 9. learning_explanation
        if any(has_word(word) for word in [
            "what is", "explain like", "concept", "why use",
            "là gì", "giải thích dễ hiểu", "tại sao dùng", "khái niệm"
        ]):
            return "learning_explanation"

        # 10. recommendation
        if any(has_word(word) for word in [
            "improve", "upgrade", "recommend", "what should i do", "next step",
            "cải thiện", "nâng cấp", "nên làm gì", "bước tiếp theo", "gợi ý"
        ]):
            return "recommendation"

        # 11. summary
        if any(has_word(word) for word in [
            "summarize", "brief", "tl;dr", "recap",
            "tóm tắt", "ngắn gọn", "ý chính"
        ]):
            return "summary"

        # 12. explanation
        if any(has_word(word) for word in [
            "how does", "how is", "explain", "walk me through", "what happens when", "flow",
            "hoạt động như thế nào", "giải thích", "luồng chạy", "cách hoạt động", "chuyện gì xảy ra khi"
        ]):
            return "explanation"

        # 13. direct_lookup
        if any(has_word(word) for word in [
            "which function", "what file", "where is", "located in", "which class", "which method",
            "what calls", "what routes", "handler", "entrypoint", "defined where",
            "hàm nào", "file nào", "nằm ở đâu", "ở đâu", "class nào", "method nào", "gọi tới", "được định nghĩa ở đâu"
        ]):
            return "direct_lookup"

        # Fallback styles
        if intent == "code_flow" or route == "structural":
            return "direct_lookup"
        if intent == "historical" or route == "historical":
            return "historical_reasoning"

        return "explanation"
