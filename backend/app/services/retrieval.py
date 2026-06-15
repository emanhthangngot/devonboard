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
            "prompt_preview": ""
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
        )
        synthesis_ms = int((time.perf_counter() - synth_start) * 1000)

        prompt = self._get_synthesis_prompt(query, structural, historical)
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

        yield {"event": "route", "data": {"route": route}}
        yield {"event": "citations", "data": {"citations": citations}}
        yield {"event": "warnings", "data": {"warnings": warnings}}

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
                    stream_generator = self._call_groq_stream(api_key, query, route, structural, historical)
                else:
                    stream_generator = self._call_gemini_stream(api_key, query, route, structural, historical)
                
                for chunk in stream_generator:
                    yielded_any = True
                    yield {"event": "token", "data": {"token": chunk}}
            except Exception as e:
                print(f"Stream generation failed: {e}")
            if not yielded_any:
                fallback = self._heuristic_synthesis(query, route, structural, historical, warnings)
                yield {"event": "token", "data": {"token": fallback}}
        else:
            fallback = self._heuristic_synthesis(query, route, structural, historical, warnings)
            yield {"event": "token", "data": {"token": fallback}}

        yield {"event": "done", "data": {}}

    def _call_gemini_stream(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
    ):
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical)
        settings = get_settings()
        model = settings.gemini_synthesis_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
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
    ):
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
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
                # limit size of any single snippet to 150 lines
                if end - start > 150:
                    end = start + 150

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
                contents.append(f"{header}\n{snippet_text}\n")

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
    ) -> str:
        settings = get_settings()
        api_key = settings.gemini_api_key

        if api_key and use_llm:
            try:
                if api_key.startswith("gsk_"):
                    result = self._call_groq(api_key, query, route, structural, historical)
                else:
                    result = self._call_gemini(api_key, query, route, structural, historical)
                
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
        return self._heuristic_synthesis(query, route, structural, historical, warnings)

    def _call_groq(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
    ) -> str | None:
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical)
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
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
    ) -> str:
        structural_text = "\n".join(f"- {item['label']}: {item['summary']}" for item in structural[:5])
        historical_text = "\n".join(f"- {item['label']}: {item['summary']}" for item in historical[:8])
        files_context = self._get_files_context(structural, historical)
        route = getattr(self, "_retrieval_mode", "hybrid")
        intent = self._intent(query)

        # Build evidence table
        evidence_lines = []
        for idx, item in enumerate(structural[:8]):
            evidence_lines.append(f"| S-{idx+1} | {item['node_id']} | {item['type']} | {item['label']} | {item['summary']} |")
        for idx, item in enumerate(historical[:8]):
            evidence_lines.append(f"| H-{idx+1} | {item['node_id']} | {item['type']} | {item['label']} | {item['summary']} |")
        evidence_table = "\n".join(evidence_lines) if evidence_lines else "No direct evidence retrieved."

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

### Required Answer Format:
For diagnosis-style, troubleshooting, or evaluation queries, you MUST use the following headers:
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
[How to verify the fix]

For other normal informational queries, you may use standard markdown headings but you MUST separate your answer into "How it works" and "Why / History" sections (if both structural and historical evidence are present), and you must still strictly cite node IDs.
"""

    def _call_gemini(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
    ) -> str | None:
        self._retrieval_mode = route
        prompt = self._get_synthesis_prompt(query, structural, historical)
        # P0 fix: API key in header (x-goog-api-key) instead of URL query parameter.
        settings = get_settings()
        model = settings.gemini_synthesis_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
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
    ) -> str:
        """Deterministic fallback synthesis when no LLM is available."""
        lowered_query = query.lower()
        intent = self._intent(query)
        
        # 1. Custom code_flow fallback response answering function/class lookups
        if intent == "code_flow":
            lines = ["### Structural Code Flow Analysis (Heuristic Fallback)"]
            
            functions = [s for s in structural if s.get("type") == "function"]
            classes = [s for s in structural if s.get("type") == "class"]
            files = [s for s in structural if s.get("type") == "file"]
            
            def file_from_node_id(node_id: str, default: str) -> str:
                parts = node_id.split(":")
                if len(parts) >= 3 and parts[0] in {"function", "class", "method"}:
                    return parts[1]
                return default
            
            if functions:
                lines.append("\n**Key Functions Found:**")
                for fn in functions[:5]:
                    fn_file = file_from_node_id(str(fn.get("node_id", "")), str(fn.get("label", "")))
                    lines.append(f"- **`{fn['label']}`** in `[node:file:{fn_file}]`")
                    if fn.get("summary"):
                        lines.append(f"  *Summary:* {fn['summary']}")
                    if fn.get("snippet"):
                        # Show the first line of the snippet as signature preview
                        first_line = fn["snippet"].strip().split("\n")[0]
                        lines.append(f"  *Signature Preview:* `{first_line}`")
            
            if classes:
                lines.append("\n**Key Classes Found:**")
                for cls in classes[:3]:
                    cls_file = file_from_node_id(str(cls.get("node_id", "")), str(cls.get("label", "")))
                    lines.append(f"- **`{cls['label']}`** in `[node:file:{cls_file}]`")
                    if cls.get("summary"):
                        lines.append(f"  *Summary:* {cls['summary']}")
            
            if files:
                lines.append("\n**Relevant Code Files:**")
                for f in files[:5]:
                    lines.append(f"- `[node:file:{f['label']}]`: {f['summary']}")
                    
            if not functions and not classes and not files:
                lines.append("No code structural evidence could be heuristic-analyzed.")
            else:
                print("WARNING: Gemini synthesis is currently disabled or unavailable. Above is the structured evidence retrieved from the codebase graph.")
                
            return "\n".join(lines)
            
        # 2. Existing fallback logic for pipeline, memory tiers, and default structural/historical summaries
        is_pipeline_query = any(k in lowered_query for k in ["pipeline", "stage", "execution", "goclaw", "run"])
        ordered_pipeline = self._ordered_pipeline_answer(structural) if (intent == "list_ordered" and is_pipeline_query) else None
        if ordered_pipeline:
            return ordered_pipeline
        memory_tiers = self._memory_tiers_answer(query, structural)
        if memory_tiers:
            return memory_tiers
        if route == "hybrid":
            return "\n\n".join(
                [
                    "**Structural impact**\n" + self._summarize("structural", structural),
                    "**Historical context**\n" + self._summarize("historical", historical),
                    "**Refactor guidance**\nUse the cited files and claims as the review boundary. Do not assume missing rationale.",
                ]
            )
        if route == "historical":
            if not historical:
                return "**Historical context**\nNo direct historical evidence found for this query. I will not infer a commit, PR, or rationale from adjacent evidence."
            return "**Historical context**\n" + self._summarize("historical", historical)
        return "**Structural impact**\n" + self._summarize("structural", structural) + (
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
        for item in evidence:
            node_id = str(item["node_id"])
            if node_id in seen:
                continue
            seen.add(node_id)
            result.append(item)
        return result
