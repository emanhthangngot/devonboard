# Spec: DevOnboard — AI Codebase Institutional Memory

This document points to the official Product Requirements Document (PRD). To ensure documentation integrity and avoid duplicate versions, please refer to the main artifact:

*   **Official PRD:** [06_prd.md](./product_artifacts/06_prd.md)

---

## Quick Summary of Objectives

*   **Feature ID:** 001-devonboard
*   **Objective:** Implement a local codebase memory system that parses files and git history to construct a local knowledge graph, powering cited Q&A search, History/Why panel, refactor risk analysis, and evidence pack generation.
*   **Target Codebase:** `nextlevelbuilder/goclaw`, branch `dev` (pinned demo commit).
*   **Privacy & Safety:** Zero external code transmission by default. Support local LLMs (Ollama) or private API configurations with an "Evidence-only" mode.
