# Artifact Alignment Checklist

---

## Product Artifact Rules

| Rule | Status | Evidence |
|---|---|---|
| Start with problem, not model | Pass | `docs/spec.md` opens with onboarding/history pain |
| Eight core artifacts exist | Pass | `docs/product_artifacts/README.md` |
| Context pack is self-contained | Pass | `00_problem_statement.md` through `05_use_cases/` and `ai_in_practice/` live inside `devonboard/` |
| PRD/spec focuses on what and why | Pass | Implementation details live in architecture/data-model/API docs |
| Out of scope is explicit | Pass | `docs/spec.md` Non-Goals |
| Roadmap uses themes/outcomes | Pass | `docs/ROADMAP.md` |
| Prototype tests riskiest assumption only | Pass | `docs/PROTOTYPE_PLAN.md` |
| Persona details are relevant | Pass | `03_target_users/user_segments_and_behaviors.md` |

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
