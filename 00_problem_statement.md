# Problem Statement

## The Problem in One Sentence

New engineers and maintainers struggle to understand complex codebases because structural knowledge, design rationale, and historical decisions are scattered across source files, commits, pull requests, issues, and senior engineers' memories, which leads to slow onboarding, risky refactors, and unreliable AI-assisted answers.

## Who Is Affected

*   **Primary group:** New software engineers joining an existing product team or open-source project.
*   **Secondary groups:** Maintainers, tech leads, code reviewers, and engineers using AI coding assistants on unfamiliar repositories.
*   **Scale:** The global developer population is large and growing; SlashData estimated 47.2 million developers worldwide in 2025, and GitHub reported more than 180 million users globally in 2025.
*   **Where / when:** This pain is most acute during first-week onboarding, incident response, large refactors, PR review, and when AI agents are asked to work in unfamiliar codebases.

## Why This Problem Exists

*   **Code explains what, not why.** Source files show current implementation but rarely preserve the reasoning behind design decisions.
*   **Historical evidence is fragmented.** Important context lives across commit bodies, PR descriptions, review comments, issue threads, Slack messages, and undocumented senior knowledge.
*   **Documentation decays.** READMEs and wikis are rarely updated at the same speed as code.
*   **AI tools lack durable repo memory.** Generic assistants can read files, but they often miss cross-file structure and historical rationale unless context is manually assembled.
*   **Review bottlenecks are growing.** AI-assisted coding increases output speed, but teams still need humans to verify whether changes are safe.

## Why It Matters Now

*   AI-assisted coding is now mainstream; Stanford HAI's 2025 AI Index reports broad enterprise AI adoption, and GitHub Copilot studies show large productivity gains on scoped tasks.
*   Faster code generation increases the cost of missing context: bigger changes can be produced before reviewers fully understand architectural and historical risk.
*   Teams increasingly need explainable, evidence-grounded AI tools rather than thin prompt wrappers.

## What "Solved" Would Look Like

*   A new engineer can ask how a subsystem works and receive cited file/function evidence.
*   A maintainer can ask why a design exists and receive commit/PR/review evidence.
*   A reviewer can ask whether a refactor is risky and see both dependency impact and historical warnings.
*   AI-generated explanations become verifiable because every key claim links back to source evidence.

## Why You Chose This

AI can write code quickly, but teams still lose time because the "why" behind existing systems is not machine-readable. DevOnboard focuses on preserving that institutional memory so engineers can move faster without becoming less careful.

## References & Further Reading

*   Stanford HAI, *Artificial Intelligence Index Report 2025*: https://arxiv.org/abs/2504.07139
*   Peng et al., *The Impact of AI on Developer Productivity: Evidence from GitHub Copilot*: https://arxiv.org/abs/2302.06590
*   Google Cloud DORA, *Accelerate State of DevOps Report 2024*: https://cloud.google.com/devops/state-of-devops
*   SlashData, Global developer population trends 2025: https://slashdata.co/

**Keywords for Further Research:** developer onboarding, codebase knowledge graph, AI-assisted software development, institutional memory, refactor risk
