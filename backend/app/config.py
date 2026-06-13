from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    target_repo_path: Path = Field(default=Path("./target_repo"), alias="TARGET_REPO_PATH")
    devonboard_graph_path: Path = Field(
        default=Path("./devonboard/knowledge-graph.json"), alias="DEVONBOARD_GRAPH_PATH"
    )
    repo_cache_path: Path = Field(default=Path("./devonboard/repos"), alias="DEVONBOARD_REPO_CACHE_PATH")
    target_repo_branch: str = Field(default="dev", alias="TARGET_REPO_BRANCH")
    target_repo_commit: str | None = Field(default=None, alias="TARGET_REPO_COMMIT")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    qdrant_url: str | None = Field(default=None, alias="QDRANT_URL")
    allow_external_llm_for_private_repo: bool = Field(
        default=False, alias="ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO"
    )
    max_commits_ingest: int = Field(default=500, alias="MAX_COMMITS_INGEST")
    results_dir: Path = Field(
        default=Path("./devonboard/results"), alias="DEVONBOARD_RESULTS_DIR"
    )
    exclude_patterns: str = Field(
        default=".env*,node_modules/**,vendor/**,dist/**,build/**,.git/**",
        alias="EXCLUDE_PATTERNS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
