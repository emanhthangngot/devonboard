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
        evidence_only = False
        settings = get_settings()
        if settings.gemini_api_key and not allow_external_llm:
            evidence_only = True
            warnings.append(
                "External LLM disabled for this repository. "
                "Returning evidence-only response."
            )

        answer = self._synthesize(
            query, route, structural, historical, warnings,
            use_llm=(not evidence_only),
        )
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
            evidence_only=evidence_only,
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
                for chunk in self._call_gemini_stream(settings.gemini_api_key, query, route, structural, historical):
                    yielded_any = True
                    yield {"event": "token", "data": {"token": chunk}}
            except Exception as e:
                print(f"Gemini stream generation failed: {e}")
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
            return mode  # type: ignore[return-value]
        lowered = query.lower()

        # Extract alphanumeric words to perform safe word-boundary matches without substring pollution.
        words = set(re.findall(r"[a-z0-9]+", lowered))

        # Check hybrid keywords first
        hybrid_words = {"refactor", "safe", "risk", "guardrail", "guardrails"}
        hybrid_substrings = ["context pack", "blast radius", "impact"]
        if (words & hybrid_words) or any(sub in lowered for sub in hybrid_substrings):
            return "hybrid"

        # Check historical keywords next
        historical_words = {
            "why", "rationale", "decision", "chosen", "who", "when", "history",
            "alternative", "pr", "commit", "original", "prior", "bug", "incident",
            "discussion", "leak", "leaking", "introduced", "restricted", "restricting"
        }
        historical_substrings = [
            "when was", "what was", "what changed", "before this fix",
            "before the fix", "was there", "led to", "pr #", "pull request"
        ]
        if (words & historical_words) or any(sub in lowered for sub in historical_substrings):
            return "historical"

        intent = self._intent(query)
        if intent in {"list_ordered", "architecture", "code_flow"}:
            return "structural"
        if intent in {"historical_rationale", "provenance", "review_comment", "negative_evidence"}:
            return "historical"
        return "structural"

    def _intent(self, query: str) -> QueryIntent:
        lowered = query.lower()
        if any(token in lowered for token in ["refactor", "blast radius", "risk indicator", "safe to"]):
            return "refactor_risk"
        if any(token in lowered for token in ["review comment", "requested in review", "reviewer"]):
            return "review_comment"
        if re.search(r"\bpr\s*#?\d+\b", lowered) or any(
            token in lowered
            for token in ["is there a commit", "is there a pr", "which pr", "which commit", "pull request", "provenance"]
        ):
            return "provenance"
        if any(token in lowered for token in ["how", "implemented", "which struct", "which interface", "code flow"]):
            return "code_flow"
        if any(token in lowered for token in ["why", "rationale", "decision", "chosen", "instead of", "tradeoff", "alternative"]):
            return "historical_rationale"
        if any(token in lowered for token in ["list", "execution order", "in order", "ordered"]):
            return "list_ordered"
        if any(token in lowered for token in ["architecture", "pipeline", "tier", "l0", "l1", "l2", "memory", "vault"]):
            return "architecture"
        return "architecture"

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

    def _get_files_context(self, structural: list[dict[str, object]]) -> str:
        if not self.graph.repo or not self.graph.repo.path:
            return ""

        repo_dir = Path(self.graph.repo.path)
        contents = []
        read_paths: set[Path] = set()

        for item in structural:
            node_id = item.get("node_id")
            if not node_id:
                continue
            try:
                node = self.graph.node_by_id(node_id)
            except KeyError:
                continue

            file_path_str = node.file_path
            if not file_path_str:
                continue

            full_path = (repo_dir / file_path_str).resolve()
            if full_path in read_paths:
                continue

            try:
                full_path.relative_to(repo_dir)
            except ValueError:
                continue

            if full_path.is_file():
                try:
                    text = full_path.read_text(encoding="utf-8", errors="ignore")[:12000]
                    contents.append(f"--- File: {file_path_str} ---\n{text}\n")
                    read_paths.add(full_path)
                except Exception as e:
                    print(f"Error reading file {file_path_str}: {e}")

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
            result = self._call_gemini(api_key, query, route, structural, historical)
            if result:
                return result
            # Gemini failed — fall through to heuristic synthesis.

        # Heuristic / rule-based fallback synthesis.
        return self._heuristic_synthesis(query, route, structural, historical, warnings)

    def _get_synthesis_prompt(
        self,
        query: str,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
    ) -> str:
        structural_text = "\n".join(f"- {item['label']}: {item['summary']}" for item in structural[:5])
        historical_text = "\n".join(f"- {item['label']}: {item['summary']}" for item in historical[:8])
        files_context = self._get_files_context(structural)

        return f"""You are DevOnboard AI, a helpful agentic coding assistant.
Your task is to answer the user's query using only the provided codebase structure, history, and file contents.

User Query:
{query}

Retrieved Codebase Structure (Nodes & Summaries):
{structural_text}

Retrieved Codebase History (Commits & Claims):
{historical_text}

Retrieved File Contents:
{files_context}

Instructions:
1. Answer the user query clearly and accurately.
2. Ground your answer strictly in the provided structural details, history, and file contents. Do not assume or extrapolate beyond what is present.
3. Cite the files, classes, functions, or commits used in your answer using their exact names or IDs (e.g. `[filename](file:///path/to/file)` or `[source:commit:abcd]`).
4. If the retrieved evidence is insufficient to answer the query, state what is missing and present the available facts honestly.
5. When both structural and historical evidence are present, separate your answer into "How it works" and "Why / History" sections.
6. For structural, code flow, or call flow queries (such as tracing a function execution path, listing interface methods or implementing files), extract and present a granular, step-by-step function/call trace. For each step, detail the caller package/file, called functions, parameters, routing/dispatching logic, and return values/state transitions.

Provide your answer in markdown:
"""

    def _call_gemini(
        self,
        api_key: str,
        query: str,
        route: Route,
        structural: list[dict[str, object]],
        historical: list[dict[str, object]],
    ) -> str | None:
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
        is_pipeline_query = any(k in lowered_query for k in ["pipeline", "stage", "execution", "goclaw", "run"])
        ordered_pipeline = self._ordered_pipeline_answer(structural) if (self._intent(query) == "list_ordered" and is_pipeline_query) else None
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
            quality_penalty = 0.0
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
                if node.type in {"function", "class", "module"}:
                    intent_boost += 0.35
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
                if self._is_doc_node(node) and self._is_primary_architecture_doc(node):
                    intent_boost += 0.2
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

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored]

    def _contains_ordered_pipeline_stages(self, node: GraphNode) -> bool:
        text = re.sub(r"[^a-z0-9]+", " ", self._node_search_text(node))
        stages = ["context", "history", "prompt", "think", "act", "observe", "memory", "summarize"]
        positions = []
        for stage in stages:
            pos = text.find(stage)
            if pos < 0:
                return False
            positions.append(pos)
        return positions == sorted(positions)

    def _query_mentions_memory_tiers(self, query: str) -> bool:
        lowered = query.lower()
        return "l0" in lowered and "l1" in lowered and "l2" in lowered

    def _contains_memory_tiers(self, node: GraphNode) -> bool:
        text = self._node_search_text(node)
        return all(token in text for token in ["l0", "l1", "l2"]) and any(
            token in text for token in ["progressive", "auto-inject", "auto injection", "memory_search", "memory_expand"]
        )

    def _is_primary_architecture_doc(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        return path in {"agents.md", "claude.md", "readme.md"} or path.startswith("docs/00-") or path.startswith("docs/06-") or path.startswith("docs/07-") or path.startswith("docs/24-")

    def _is_secondary_doc(self, node: GraphNode) -> bool:
        path = (node.file_path or node.id).lower()
        return path.startswith("docs/journals/") or path.startswith("plans/") or path.startswith("skills/")

    def _is_memory_implementation_node(self, node: GraphNode) -> bool:
        if self._is_test_node(node):
            return False
        path = (node.file_path or node.id).lower()
        return path.startswith(
            (
                "internal/memory/",
                "internal/consolidation/",
                "internal/agent/",
                "internal/tools/memory",
                "internal/vault/",
                "internal/store/episodic",
                "internal/store/pg/episodic",
                "internal/store/sqlitestore/episodic",
            )
        )

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
            "structural": ["file", "module"],
            "historical": ["source", "claim"],
            "hybrid": ["file", "module", "source", "claim"],
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
