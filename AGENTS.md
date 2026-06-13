# Project Agent Instructions

This repository uses a local, ignored `.agent/` directory for project-specific
Codex context. At the start of any task in this repository, check whether
`.agent/codex.md` exists. If it exists, read it before planning or editing.

Treat `.agent/codex.md` as the routing map for DevOnboard work. When it points
to role, workflow, or checklist files under `.agent/`, read only the files that
match the current task.

Default workflow:

- Follow `.agent/workflows/spec-first-tdd.md` for implementation tasks.
- For frontend work, read `.agent/roles/frontend.md` and
  `.agent/checklists/frontend-quality.md`.
- For backend or API work, read `.agent/roles/backend.md` and
  `.agent/checklists/backend-api.md`.
- For AI, RAG, extraction, synthesis, or evidence work, read the relevant
  `.agent/roles/ai-engine.md`, `.agent/roles/rag.md`, and
  `.agent/checklists/rag-evidence.md` files.

The `.agent/` directory is local context and should remain ignored by Git.
