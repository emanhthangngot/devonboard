import subprocess
from pathlib import Path

from backend.app.graph.ids import edge_id, entity_id, file_id, source_commit_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph
from backend.app.ingest.rationale_extractor import RationaleExtractor


class GitHistoryIngestor:
    def __init__(self, repo_path: Path, graph: KnowledgeGraph, max_commits: int) -> None:
        self.repo_path = repo_path.resolve()
        self.graph = graph
        self.max_commits = max_commits
        self._nodes_by_id = {node.id: node for node in self.graph.nodes}
        self._edges_by_id = {edge.id: edge for edge in self.graph.edges}

    def ingest(self) -> KnowledgeGraph:
        for sha in self._commit_shas():
            self._ingest_commit(sha)

        # Enforce GITHUB_TOKEN enrichment for issues, PRs, and reviews if configured
        from backend.app.config import get_settings
        settings = get_settings()
        if settings.github_token:
            try:
                from backend.app.ingest.github_fetcher import GitHubFetcher
                GitHubFetcher(self.graph, settings.github_token).enrich()
            except Exception as e:
                print(f"Failed to enrich graph with GitHub metadata: {e}")

        # Sync back helper maps before RationaleExtractor runs
        self._nodes_by_id = {node.id: node for node in self.graph.nodes}
        self._edges_by_id = {edge.id: edge for edge in self.graph.edges}

        # Extract rationales from all sources
        RationaleExtractor(self.graph).extract()

        # Final sort once at the end
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
        return node_id in self._nodes_by_id

    def _upsert_node(self, node: GraphNode) -> None:
        if node.id in self._nodes_by_id:
            existing = self._nodes_by_id[node.id]
            existing.name = node.name or existing.name
            existing.summary = node.summary or existing.summary
            existing.tags = sorted(set(existing.tags).union(node.tags))
            existing.metadata = {**existing.metadata, **node.metadata}
        else:
            self._nodes_by_id[node.id] = node
            self.graph.nodes.append(node)

    def _upsert_edge(self, edge: GraphEdge) -> None:
        if edge.id in self._edges_by_id:
            existing = self._edges_by_id[edge.id]
            existing.summary = edge.summary or existing.summary
            existing.weight = max(existing.weight, edge.weight)
            existing.metadata = {**existing.metadata, **edge.metadata}
        else:
            self._edges_by_id[edge.id] = edge
            self.graph.edges.append(edge)
