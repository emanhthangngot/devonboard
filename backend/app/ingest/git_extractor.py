import subprocess
from pathlib import Path

from backend.app.graph.ids import edge_id, entity_id, file_id, source_commit_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph


class GitHistoryIngestor:
    def __init__(self, repo_path: Path, graph: KnowledgeGraph, max_commits: int) -> None:
        self.repo_path = repo_path.resolve()
        self.graph = graph
        self.max_commits = max_commits

    def ingest(self) -> KnowledgeGraph:
        for sha in self._commit_shas():
            self._ingest_commit(sha)
        self.graph.nodes.sort(key=lambda node: node.id)
        self.graph.edges.sort(key=lambda edge: edge.id)
        return self.graph

    def _commit_shas(self) -> list[str]:
        output = self._git("rev-list", f"--max-count={self.max_commits}", "HEAD")
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _ingest_commit(self, sha: str) -> None:
        metadata = self._commit_metadata(sha)
        files_touched = self._files_touched(sha)
        source = GraphNode(
            id=source_commit_id(sha),
            type="source",
            name=metadata["subject"],
            summary=metadata["body"] or metadata["subject"],
            tags=["git", "commit"],
            metadata={
                "kind": "commit",
                "hash": sha,
                "author": metadata["author"],
                "authorEmail": metadata["email"],
                "date": metadata["date"],
                "filesTouched": files_touched,
            },
        )
        self._upsert_node(source)

        author = GraphNode(
            id=entity_id("git", metadata["email"] or metadata["author"]),
            type="entity",
            name=metadata["author"],
            summary=f"Git author {metadata['author']}.",
            tags=["author", "git"],
            metadata={"email": metadata["email"]},
        )
        self._upsert_node(author)
        self._upsert_edge(
            GraphEdge(
                id=edge_id(source.id, author.id, "authored_by"),
                source=source.id,
                target=author.id,
                type="authored_by",
                summary="Commit authored by entity.",
                weight=1.0,
            )
        )

        for touched in files_touched:
            target_id = file_id(touched)
            if not self._has_node(target_id):
                self._upsert_node(
                    GraphNode(
                        id=target_id,
                        type="file",
                        name=Path(touched).name,
                        summary=f"File touched by commit {sha[:12]}.",
                        tags=["file"],
                        filePath=touched,
                    )
                )
            self._upsert_edge(
                GraphEdge(
                    id=edge_id(source.id, target_id, "documents"),
                    source=source.id,
                    target=target_id,
                    type="documents",
                    summary="Commit touches file.",
                    weight=1.0,
                )
            )

    def _commit_metadata(self, sha: str) -> dict[str, str]:
        output = self._git("show", "-s", "--format=%an%x1f%ae%x1f%aI%x1f%s%x1f%b", sha)
        author, email, date, subject, body = (output.split("\x1f", 4) + [""])[:5]
        return {
            "author": author.strip(),
            "email": email.strip(),
            "date": date.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
        }

    def _files_touched(self, sha: str) -> list[str]:
        output = self._git("show", "--name-only", "--pretty=format:", sha)
        return sorted({line.strip() for line in output.splitlines() if line.strip()})

    def _git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.repo_path), *args], text=True)

    def _has_node(self, node_id: str) -> bool:
        return any(node.id == node_id for node in self.graph.nodes)

    def _upsert_node(self, node: GraphNode) -> None:
        for index, existing in enumerate(self.graph.nodes):
            if existing.id == node.id:
                self.graph.nodes[index] = existing.model_copy(
                    update={
                        "name": node.name or existing.name,
                        "summary": node.summary or existing.summary,
                        "tags": sorted(set(existing.tags).union(node.tags)),
                        "metadata": {**existing.metadata, **node.metadata},
                    }
                )
                return
        self.graph.nodes.append(node)

    def _upsert_edge(self, edge: GraphEdge) -> None:
        if any(existing.id == edge.id for existing in self.graph.edges):
            return
        self.graph.edges.append(edge)
