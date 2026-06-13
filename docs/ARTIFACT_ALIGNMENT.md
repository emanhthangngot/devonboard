# Artifact Alignment Checklist

---

## Product Artifact Rules

| Rule | Status | Evidence |
|---|---|---|
| Start with problem, not model | Pass | [00_problem_statement.md](./product_artifacts/00_problem_statement.md) and [06_prd.md](./product_artifacts/06_prd.md) open with onboarding/history pain |
| Eight core artifacts exist | Pass | [product_artifacts/README.md](./product_artifacts/README.md) lists `00_problem_statement.md` through `07_prototype.md` |
| Context pack is self-contained | Pass | `00_problem_statement.md` through `05_use_cases/` and `ai_in_practice/` live inside `devonboard/` |
| PRD/spec focuses on what and why | Pass | [06_prd.md](./product_artifacts/06_prd.md) focuses on user outcomes, implementation details are separated |
| Out of scope is explicit | Pass | [06_prd.md](./product_artifacts/06_prd.md) "Scope - Out of Scope" section |
| Roadmap uses themes/outcomes | Pass | [05_product_roadmap.md](./product_artifacts/05_product_roadmap.md) |
| Prototype tests riskiest assumption only | Pass | [07_prototype.md](./product_artifacts/07_prototype.md) |
| Persona details are relevant | Pass | [02_persona.md](./product_artifacts/02_persona.md) and `03_target_users/` |

---

## AI Product Rules

| Rule | Status | Evidence |
|---|---|---|
| Avoid thin-wrapper risk | Pass | Graph, history ingest, claims, citations |
| Human-in-the-loop | Pass | Raw evidence, unsupported-answer feedback, retry controls |
| Explainable AI | Pass | Citation cards and History/Why panel |
| Defensive UX | Pass | Missing evidence, stale graph, partial ingest states |
| Measure task success | Pass | Time-to-useful-answer, citation coverage, evidence usefulness, human quality score |
| Address hallucination risk | Pass | Conservative claim extraction and rejection rules |
| Address security/IP risk | Pass | Evidence-only/private-repo mode and excluded-source rules |
| Avoid API drift | Pass | `docs/api-spec.json`, backend docs, and data model use the same endpoint and metric contract |

---

## Locked Demo Decisions

- Benchmark query set: the five questions listed in `docs/AI.md`.
- Demo target: `nextlevelbuilder/goclaw`, branch `dev`, pinned by `TARGET_REPO_COMMIT`.
- Source availability without private tokens: local source files and local Git commits are available; GitHub PR/review/issue metadata is optional and must degrade to commit-only ingest when unavailable.
- Private/proprietary source handling: external LLM calls are disabled unless `ALLOW_EXTERNAL_LLM_FOR_PRIVATE_REPO=true`; evidence-only retrieval/export remains available.
