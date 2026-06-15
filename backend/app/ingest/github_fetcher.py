import json
import re
import urllib.request

from backend.app.graph.ids import edge_id, entity_id, file_id, source_pr_id
from backend.app.graph.models import GraphEdge, GraphNode, KnowledgeGraph

GITHUB_PER_PAGE = 100
GITHUB_MAX_PAGES = 10


class GitHubFetcher:
    def __init__(self, graph: KnowledgeGraph, token: str) -> None:
        self.graph = graph
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "DevOnboard-App",
            "Accept": "application/vnd.github.v3+json",
        }
        self._nodes_by_id = {node.id: node for node in self.graph.nodes}
        self._edges_by_id = {edge.id: edge for edge in self.graph.edges}

    def enrich(self) -> None:
        if not self.graph.repo or not self.graph.repo.url:
            return

        # Extract owner and repo from URL
        # Matches formats like: https://github.com/owner/repo or https://github.com/owner/repo.git
        match = re.search(r"github\.com/([^/]+)/([^/.]+)", self.graph.repo.url)
        if not match:
            return
        owner, repo = match.groups()

        # 1. Fetch Pull Requests
        for pr in self._get_paginated(f"/repos/{owner}/{repo}/pulls?state=all"):
            self._ingest_pr(owner, repo, pr)

        # 2. Fetch Issues
        for issue in self._get_paginated(f"/repos/{owner}/{repo}/issues?state=all"):
            # GitHub issues API returns PRs as well; check pull_request key.
            if "pull_request" in issue:
                continue
            self._ingest_issue(issue)

        # 3. Create cross-references (cites edges) from commit messages or PR text
        self._create_cross_references()

    def _get(self, path: str):
        url = f"https://api.github.com{path}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"GitHub API request failed to {path}: {e}")
            return None

    def _get_paginated(self, path: str, *, max_pages: int = GITHUB_MAX_PAGES) -> list[dict]:
        items: list[dict] = []
        separator = "&" if "?" in path else "?"
        for page in range(1, max_pages + 1):
            payload = self._get(
                f"{path}{separator}per_page={GITHUB_PER_PAGE}&page={page}"
            )
            if not payload:
                break
            if not isinstance(payload, list):
                break
            items.extend(item for item in payload if isinstance(item, dict))
            if len(payload) < GITHUB_PER_PAGE:
                break
        return items

    def _ingest_pr(self, owner: str, repo: str, pr: dict) -> None:
        number = pr.get("number")
        if not number:
            return

        pr_node_id = source_pr_id(number)
        user = pr.get("user", {}) or {}
        username = user.get("login", "unknown")

        files = self._get_paginated(f"/repos/{owner}/{repo}/pulls/{number}/files")
        touched_files = sorted(
            {
                filename
                for item in files
                if isinstance(filename := item.get("filename"), str) and filename
            }
        )

        pr_node = GraphNode(
            id=pr_node_id,
            type="source",
            name=f"PR #{number}: {pr.get('title')}",
            summary=pr.get("body") or f"Pull request #{number} on GitHub.",
            tags=["git", "pr", pr.get("state", "open")],
            metadata={
                "kind": "pr",
                "number": number,
                "state": pr.get("state"),
                "url": pr.get("html_url"),
                "date": pr.get("created_at"),
                "author": username,
                "filesTouched": touched_files,
            },
        )
        self._upsert_node(pr_node)

        # Author entity
        author_id = entity_id("github", username)
        author_node = GraphNode(
            id=author_id,
            type="entity",
            name=username,
            summary=f"GitHub user {username}.",
            tags=["author", "github"],
            metadata={"url": user.get("html_url")},
        )
        self._upsert_node(author_node)

        # Edge from PR to author
        self._upsert_edge(
            GraphEdge(
                id=edge_id(pr_node_id, author_id, "authored_by"),
                source=pr_node_id,
                target=author_id,
                type="authored_by",
                summary="PR authored by entity.",
                weight=1.0,
            )
        )

        # Link PR to merge commit if it exists
        merge_commit_sha = pr.get("merge_commit_sha")
        if merge_commit_sha:
            commit_node_id = f"source:commit:{merge_commit_sha}"
            # Check if this commit node exists in our graph
            if self._has_node(commit_node_id):
                self._upsert_edge(
                    GraphEdge(
                        id=edge_id(pr_node_id, commit_node_id, "builds_on"),
                        source=pr_node_id,
                        target=commit_node_id,
                        type="builds_on",
                        summary="PR merges into commit.",
                        weight=1.0,
                    )
                )

        # Fetch and ingest reviews for this PR
        for filename in touched_files:
            target_file_id = file_id(filename)
            if not self._has_node(target_file_id):
                continue
            self._upsert_edge(
                GraphEdge(
                    id=edge_id(target_file_id, pr_node_id, "cites"),
                    source=target_file_id,
                    target=pr_node_id,
                    type="cites",
                    summary=f"File modified in PR #{number}.",
                    weight=1.0,
                )
            )

        for review in self._get_paginated(f"/repos/{owner}/{repo}/pulls/{number}/reviews"):
            self._ingest_review(pr_node_id, number, review)

    def _ingest_review(self, pr_node_id: str, pr_number: int, review: dict) -> None:
        rid = review.get("id")
        if not rid:
            return

        review_node_id = f"source:review:{rid}"
        user = review.get("user", {}) or {}
        username = user.get("login", "unknown")

        review_node = GraphNode(
            id=review_node_id,
            type="source",
            name=f"Review on PR #{pr_number} by {username}",
            summary=review.get("body") or f"Review on PR #{pr_number} with state {review.get('state')}.",
            tags=["git", "review", review.get("state", "commented").lower()],
            metadata={
                "kind": "review",
                "state": review.get("state"),
                "url": review.get("html_url"),
                "date": review.get("submitted_at"),
            },
        )
        self._upsert_node(review_node)

        # Link review to PR
        self._upsert_edge(
            GraphEdge(
                id=edge_id(review_node_id, pr_node_id, "cites"),
                source=review_node_id,
                target=pr_node_id,
                type="cites",
                summary="Review comments on PR.",
                weight=1.0,
            )
        )

        # Author entity
        author_id = entity_id("github", username)
        author_node = GraphNode(
            id=author_id,
            type="entity",
            name=username,
            summary=f"GitHub user {username}.",
            tags=["author", "github"],
            metadata={"url": user.get("html_url")},
        )
        self._upsert_node(author_node)

        # Edge from review to author
        self._upsert_edge(
            GraphEdge(
                id=edge_id(review_node_id, author_id, "authored_by"),
                source=review_node_id,
                target=author_id,
                type="authored_by",
                summary="Review submitted by reviewer.",
                weight=1.0,
            )
        )

    def _ingest_issue(self, issue: dict) -> None:
        number = issue.get("number")
        if not number:
            return

        issue_node_id = f"source:issue:{number}"
        user = issue.get("user", {}) or {}
        username = user.get("login", "unknown")

        issue_node = GraphNode(
            id=issue_node_id,
            type="source",
            name=f"Issue #{number}: {issue.get('title')}",
            summary=issue.get("body") or f"Issue #{number} on GitHub.",
            tags=["git", "issue", issue.get("state", "open")],
            metadata={
                "kind": "issue",
                "number": number,
                "state": issue.get("state"),
                "url": issue.get("html_url"),
                "date": issue.get("created_at"),
                "author": username,
            },
        )
        self._upsert_node(issue_node)

        # Author entity
        author_id = entity_id("github", username)
        author_node = GraphNode(
            id=author_id,
            type="entity",
            name=username,
            summary=f"GitHub user {username}.",
            tags=["author", "github"],
            metadata={"url": user.get("html_url")},
        )
        self._upsert_node(author_node)

        # Edge from issue to author
        self._upsert_edge(
            GraphEdge(
                id=edge_id(issue_node_id, author_id, "authored_by"),
                source=issue_node_id,
                target=author_id,
                type="authored_by",
                summary="Issue created by entity.",
                weight=1.0,
            )
        )

    def _create_cross_references(self) -> None:
        # Scan all commit and PR nodes in the graph for mentions like "#12"
        # If they mention it, and the issue or PR node exists, create a cites edge.
        issue_ids = {node.id: node for node in self.graph.nodes if node.type == "source" and node.metadata.get("kind") in {"issue", "pr"}}

        for node in list(self.graph.nodes):
            if node.type != "source" or node.metadata.get("kind") not in {"commit", "pr"}:
                continue

            text_to_search = f"{node.name} {node.summary}"
            # Find all patterns like #12
            mentions = re.findall(r"#(\d+)", text_to_search)
            for num in set(mentions):
                # Try PR first
                target_id = source_pr_id(num)
                if target_id not in issue_ids:
                    target_id = f"source:issue:{num}"

                if target_id in issue_ids:
                    self._upsert_edge(
                        GraphEdge(
                            id=edge_id(node.id, target_id, "cites"),
                            source=node.id,
                            target=target_id,
                            type="cites",
                            summary="Source mentions/cites issue or PR.",
                            weight=0.8,
                        )
                    )

    def _upsert_node(self, node: GraphNode) -> None:
        if node.id in self._nodes_by_id:
            existing = self._nodes_by_id[node.id]
            existing.name = node.name or existing.name
            existing.summary = node.summary or existing.summary
            existing.tags = sorted(set(existing.tags).union(node.tags))
            existing.file_path = node.file_path or existing.file_path
            existing.line_range = node.line_range or existing.line_range
            existing.metadata = {**existing.metadata, **node.metadata}
            return
        self._nodes_by_id[node.id] = node
        self.graph.nodes.append(node)

    def _upsert_edge(self, edge: GraphEdge) -> None:
        if edge.id in self._edges_by_id:
            existing = self._edges_by_id[edge.id]
            existing.summary = edge.summary or existing.summary
            existing.weight = max(existing.weight, edge.weight)
            existing.metadata = {**existing.metadata, **edge.metadata}
            return
        self._edges_by_id[edge.id] = edge
        self.graph.edges.append(edge)

    def _has_node(self, node_id: str) -> bool:
        return node_id in self._nodes_by_id
