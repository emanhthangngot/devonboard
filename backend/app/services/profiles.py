from dataclasses import dataclass, field

@dataclass
class ProjectProfile:
    name: str
    primary_architecture_docs: list[str] = field(default_factory=list)
    secondary_docs: list[str] = field(default_factory=list)
    boost_files: list[str] = field(default_factory=list)
    pipeline_stages: list[str] = field(default_factory=list)
    memory_tiers: list[str] = field(default_factory=list)
    memory_implementation_prefixes: list[str] = field(default_factory=list)


generic_profile = ProjectProfile(
    name="generic",
    primary_architecture_docs=["readme.md"],
    secondary_docs=[],
    boost_files=[],
    pipeline_stages=[],
    memory_tiers=[],
    memory_implementation_prefixes=[],
)

devonboard_profile = ProjectProfile(
    name="devonboard",
    primary_architecture_docs=[
        "agents.md",
        "claude.md",
        "readme.md",
        "docs/00-",
        "docs/06-",
        "docs/07-",
        "docs/24-",
    ],
    secondary_docs=["docs/journals/", "plans/", "skills/"],
    boost_files=[
        "backend/app/main.py",
        "backend/app/routers/query.py",
        "backend/app/services/retrieval.py",
        "backend/app/services/vector_index.py",
        "backend/app/scanner/structure_scanner.py",
        "backend/app/graph/graph_store.py",
        "backend/app/graph/models.py",
        "backend/app/graph/ids.py",
        "backend/README.md",
    ],
    pipeline_stages=["context", "history", "prompt", "think", "act", "observe", "memory", "summarize"],
    memory_tiers=["l0", "l1", "l2"],
    memory_implementation_prefixes=[
        "internal/memory/",
        "internal/consolidation/",
        "internal/agent/",
        "internal/tools/memory",
        "internal/vault/",
        "internal/store/episodic",
        "internal/store/pg/episodic",
        "internal/store/sqlitestore/episodic",
        "backend/app/services/vector_index.py",
    ],
)


def get_project_profile(repo_name: str) -> ProjectProfile:
    name_lower = (repo_name or "").lower()
    if "devonboard" in name_lower or "dev-onboard" in name_lower:
        return devonboard_profile
    # For goclaw or nextlevelbuilder/goclaw tests, let's keep the previous behavior if it maps:
    if "goclaw" in name_lower:
        return devonboard_profile
    return generic_profile
