import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from backend.app.graph.models import GraphNode, KnowledgeGraph

INDEXED_NODE_TYPES = {"file", "module", "source", "claim"}


@dataclass
class VectorHit:
    node_id: str
    score: float
    payload: dict[str, Any]


@dataclass
class LocalPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str, dimensions: int, batch_size: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.batch_size = max(1, batch_size)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for index in range(0, len(texts), self.batch_size):
            batch = texts[index : index + self.batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        body = json.dumps(
            {
                "requests": [
                    {
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": text}]},
                        "outputDimensionality": self.dimensions,
                    }
                    for text in texts
                ]
            }
        ).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        embeddings = payload.get("embeddings", [])
        return [list(item.get("values", [])) for item in embeddings]


class VectorIndexService:
    def __init__(
        self,
        qdrant_url: str | None,
        collection: str,
        vector_size: int,
        *,
        client: Any | None = None,
        embedder: Any | None = None,
    ) -> None:
        self.qdrant_url = qdrant_url
        self.collection = collection
        self.vector_size = vector_size
        self.client = client
        self.embedder = embedder

    @classmethod
    def from_settings(cls) -> "VectorIndexService | None":
        from backend.app.config import get_settings

        settings = get_settings()
        if not settings.qdrant_url or not settings.gemini_api_key:
            return None
        return cls(
            qdrant_url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            vector_size=settings.embedding_dimensions,
            embedder=GeminiEmbedder(
                api_key=settings.gemini_api_key,
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                batch_size=settings.embedding_batch_size,
            ),
        )

    def is_available(self) -> bool:
        try:
            return self._client() is not None and self.embedder is not None
        except Exception:
            return False

    def status(self) -> dict[str, Any]:
        if not self.qdrant_url:
            return {"configured": False, "integrated": True, "reachable": False}
        try:
            client = self._client()
            collection_exists = bool(client.collection_exists(self.collection))
            return {
                "configured": True,
                "integrated": True,
                "reachable": True,
                "collection": self.collection,
                "collection_exists": collection_exists,
                "vector_size": self.vector_size,
                "url": self.qdrant_url,
            }
        except Exception as exc:
            return {
                "configured": True,
                "integrated": True,
                "reachable": False,
                "collection": self.collection,
                "url": self.qdrant_url,
                "error": str(exc),
            }

    def rebuild(self, graph: KnowledgeGraph) -> dict[str, Any]:
        if not self.qdrant_url or not self.embedder:
            return {"indexed_points": 0, "skipped": True, "reason": "vector index not configured"}

        client = self._client()
        self._ensure_collection(client)
        nodes = [node for node in graph.nodes if node.type in INDEXED_NODE_TYPES]
        texts = [self._node_text(node) for node in nodes]
        vectors = self.embedder.embed_texts(texts) if texts else []
        points = [
            self._point(node=node, vector=vector, graph=graph)
            for node, vector in zip(nodes, vectors, strict=False)
            if len(vector) == self.vector_size
        ]
        if points:
            client.upsert(collection_name=self.collection, points=points)
        return {
            "indexed_points": len(points),
            "skipped": False,
            "collection": self.collection,
            "vector_size": self.vector_size,
        }

    def search(
        self,
        query: str,
        *,
        node_types: list[str] | None = None,
        limit: int = 8,
    ) -> list[VectorHit]:
        if not self.qdrant_url or not self.embedder:
            return []
        client = self._client()
        try:
            if not client.collection_exists(self.collection):
                return []
        except Exception:
            return []
        vectors = self.embedder.embed_texts([query])
        if not vectors:
            return []
        query_filter = self._node_type_filter(node_types)
        result = client.query_points(
            collection_name=self.collection,
            query=vectors[0],
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        points = getattr(result, "points", result)
        hits: list[VectorHit] = []
        for point in points or []:
            payload = dict(getattr(point, "payload", {}) or {})
            node_id = payload.get("graph_node_id")
            if not isinstance(node_id, str):
                continue
            hits.append(
                VectorHit(
                    node_id=node_id,
                    score=float(getattr(point, "score", 0.0) or 0.0),
                    payload=payload,
                )
            )
        return hits

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.qdrant_url:
            raise RuntimeError("Qdrant URL is not configured")
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("qdrant-client package is not installed") from exc
        self.client = QdrantClient(url=self.qdrant_url, timeout=2, check_compatibility=False)
        return self.client

    def _ensure_collection(self, client: Any) -> None:
        try:
            from qdrant_client import models
        except ImportError:
            models = None

        if not client.collection_exists(self.collection):
            vectors_config = (
                models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE)
                if models is not None
                else {"size": self.vector_size, "distance": "Cosine"}
            )
            client.create_collection(
                collection_name=self.collection,
                vectors_config=vectors_config,
            )
        for field_name in ["graph_node_id", "node_type", "repo_name", "branch", "file_path"]:
            try:
                client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field_name,
                    field_schema=(
                        models.PayloadSchemaType.KEYWORD if models is not None else "keyword"
                    ),
                )
            except Exception:
                pass

    def _point(self, node: GraphNode, vector: list[float], graph: KnowledgeGraph) -> Any:
        try:
            from qdrant_client import models
        except ImportError:
            models = None

        point_id = str(uuid5(NAMESPACE_URL, node.id))
        payload = self._payload(node, graph)
        if models is None:
            return LocalPoint(id=point_id, vector=vector, payload=payload)

        return models.PointStruct(
            id=point_id,
            vector=vector,
            payload=payload,
        )

    def _payload(self, node: GraphNode, graph: KnowledgeGraph) -> dict[str, Any]:
        generated_at = graph.generated_at
        if isinstance(generated_at, datetime):
            generated = generated_at.isoformat()
        else:
            generated = str(generated_at)
        return {
            "graph_node_id": node.id,
            "node_type": node.type,
            "repo_name": graph.repo.name,
            "branch": graph.repo.branch,
            "file_path": node.file_path,
            "source_kind": node.metadata.get("kind"),
            "evidence_type": node.metadata.get("evidence_type") or self._evidence_type(node),
            "snippet": node.metadata.get("document_snippet") or node.metadata.get("snippet") or node.summary,
            "tags": node.tags,
            "graph_generated_at": generated,
        }

    def _node_text(self, node: GraphNode) -> str:
        parts = [node.id, node.type, node.name, node.summary, " ".join(node.tags)]
        if node.file_path:
            parts.append(node.file_path)
        kind = node.metadata.get("kind")
        if kind:
            parts.append(str(kind))
        for key in ("document_snippet", "snippet", "body", "title", "description"):
            value = node.metadata.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                parts.extend(str(item) for item in value[:8])
            else:
                parts.append(str(value))
        return "\n".join(part for part in parts if part)

    def _evidence_type(self, node: GraphNode) -> str:
        if node.type == "source":
            return str(node.metadata.get("kind", "commit"))
        if node.type == "file" and str(node.metadata.get("language", "")).lower() in {"markdown", "text", "rst"}:
            return "doc"
        return node.type

    def _node_type_filter(self, node_types: list[str] | None) -> Any | None:
        if not node_types:
            return None
        try:
            from qdrant_client import models
        except ImportError:
            return {"must": [{"key": "node_type", "match": {"any": node_types}}]}
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="node_type",
                    match=models.MatchAny(any=node_types),
                )
            ]
        )
