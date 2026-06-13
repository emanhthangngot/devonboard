# DevOnboard Context Pack

This repository contains product and technical context for **DevOnboard**, an AI codebase onboarding system that turns code structure and development history into cited institutional memory.

DevOnboard helps engineers answer:

- how a subsystem works;
- why it was designed that way;
- which commits, PRs, issues, and reviews explain it;
- what risks matter before refactoring.

---

## Folder Structure

```text
00_problem_statement.md
01_market_and_domain/
02_theme_deep_dive/
03_target_users/
04_case_studies/
05_use_cases/
docs/
ai_in_practice/
```

---

## How To Use

Start with `00_problem_statement.md`, then read the market, theme, users, case studies, and use cases. The `docs/` directory contains the technical and product implementation direction for the DevOnboard MVP.

---

## Core Product Idea

DevOnboard builds a local knowledge graph from a target repository, git history, and GitHub metadata. It links current code artifacts to historical evidence and extracted design-rationale claims, then uses that graph to power cited Q&A, a History/Why inspector, and benchmark comparisons.
