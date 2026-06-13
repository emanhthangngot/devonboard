import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


@dataclass(frozen=True)
class ResolvedRepository:
    path: Path
    name: str
    url: str | None
    branch: str
    commit: str | None


def is_github_url(value: str) -> bool:
    return bool(GITHUB_URL_RE.match(value.strip()))


def normalize_github_url(value: str) -> tuple[str, str, str]:
    match = GITHUB_URL_RE.match(value.strip())
    if not match:
        raise ValueError("Only public HTTPS GitHub repository URLs are supported.")
    owner = match.group("owner")
    repo = match.group("repo")
    return owner, repo, f"https://github.com/{owner}/{repo}.git"


def resolve_repository_input(
    repo_input: str | Path,
    branch: str,
    commit: str | None,
    cache_root: Path,
) -> ResolvedRepository:
    value = str(repo_input).strip()
    if is_github_url(value):
        owner, repo, normalized_url = normalize_github_url(value)
        path = cache_root / f"{owner}__{repo}"
        resolved_branch = _sync_github_repo(path=path, url=normalized_url, branch=branch, commit=commit)
        return ResolvedRepository(
            path=path.resolve(),
            name=repo,
            url=normalized_url,
            branch=resolved_branch,
            commit=commit,
        )

    path = Path(value).expanduser()
    return ResolvedRepository(
        path=path,
        name=path.name or "repository",
        url=None,
        branch=branch,
        commit=commit,
    )


def _sync_github_repo(path: Path, url: str, branch: str, commit: str | None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    requested_branch = branch.strip()
    if not path.exists():
        try:
            clone_command = ["git", "clone", url, str(path)]
            if requested_branch:
                clone_command[2:2] = ["--branch", requested_branch]
            subprocess.check_call(clone_command)
        except subprocess.CalledProcessError:
            if requested_branch != "dev":
                raise
            shutil.rmtree(path, ignore_errors=True)
            subprocess.check_call(["git", "clone", url, str(path)])
    else:
        if not (path / ".git").exists():
            raise ValueError(f"Repository cache path exists but is not a git repo: {path}")
        origin = subprocess.check_output(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            text=True,
        ).strip()
        if _normalize_remote(origin) != _normalize_remote(url):
            raise ValueError(f"Repository cache remote mismatch for {path}.")
        dirty = subprocess.check_output(
            ["git", "-C", str(path), "status", "--porcelain"],
            text=True,
        ).strip()
        if dirty:
            raise ValueError(f"Repository cache has local changes: {path}")
        subprocess.check_call(["git", "-C", str(path), "fetch", "--prune", "origin"])
        checkout_branch = requested_branch or _default_remote_branch(path)
        try:
            subprocess.check_call(["git", "-C", str(path), "checkout", checkout_branch])
        except subprocess.CalledProcessError:
            if requested_branch != "dev":
                raise
            checkout_branch = _default_remote_branch(path)
            subprocess.check_call(["git", "-C", str(path), "checkout", checkout_branch])

    current_branch = _current_branch(path)
    if commit:
        subprocess.check_call(["git", "-C", str(path), "checkout", commit])
    else:
        subprocess.check_call(["git", "-C", str(path), "pull", "--ff-only", "origin", current_branch])
    return current_branch


def _normalize_remote(value: str) -> str:
    return value.removesuffix(".git").removesuffix("/")


def _current_branch(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "branch", "--show-current"],
        text=True,
    ).strip()


def _default_remote_branch(path: Path) -> str:
    subprocess.check_call(["git", "-C", str(path), "remote", "set-head", "origin", "-a"])
    symbolic_ref = subprocess.check_output(
        ["git", "-C", str(path), "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
        text=True,
    ).strip()
    return symbolic_ref.removeprefix("origin/")
