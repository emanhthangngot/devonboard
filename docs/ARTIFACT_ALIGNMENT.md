# Artifact Alignment Checklist

---

## Product Artifact Rules

| Rule | Status | Evidence |
|---|---|---|
| Start with problem, not model | Pass | `docs/spec.md` opens with onboarding/history pain |
| PRD/spec focuses on what and why | Pass after cleanup | Implementation details moved to architecture/tasks |
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
| Measure task success | Pass | Time-to-useful-answer, citation coverage, evidence usefulness |
| Address hallucination risk | Pass | Conservative claim extraction and rejection rules |

---

## Remaining Review Questions

- Which exact benchmark questions will be used in the live demo?
- Which target repository branch is frozen for the demo?
- Which source types are available without private tokens?
