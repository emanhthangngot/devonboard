import re
from pathlib import PurePosixPath


def normalize_repo_path(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unnamed"


def file_id(path: str) -> str:
    return f"file:{normalize_repo_path(path)}"


def function_id(path: str, name: str) -> str:
    return f"function:{normalize_repo_path(path)}:{name}"


def module_id(path: str) -> str:
    return f"module:{normalize_repo_path(path)}"


def source_commit_id(commit_sha: str) -> str:
    return f"source:commit:{commit_sha}"


def source_pr_id(number: int | str) -> str:
    return f"source:pr:{number}"


def claim_id(name: str) -> str:
    return f"claim:{slugify(name)}"


def entity_id(kind: str, value: str) -> str:
    return f"entity:{slugify(kind)}:{slugify(value)}"


def edge_id(source: str, target: str, edge_type: str) -> str:
    return f"edge:{edge_type}:{source}->{target}"
