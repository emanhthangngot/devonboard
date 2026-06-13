# Use Cases and Existing Alternatives

## Concrete Use Cases

### Use Case 1: First-Day Codebase Onboarding

*   **Trigger:** A new engineer joins a team and receives their first repo task.
*   **User wants:** Understand the main subsystems, key files, and how execution flows.
*   **Ideal outcome:** They get a cited architecture explanation and know which files to inspect first.

### Use Case 2: Design-Rationale Lookup

*   **Trigger:** An engineer finds surprising code and asks why it was implemented that way.
*   **User wants:** Find the commit/PR/review evidence behind the design.
*   **Ideal outcome:** DevOnboard shows a concise rationale summary with links to historical evidence.

### Use Case 3: Refactor-Risk Check

*   **Trigger:** A maintainer wants to change a shared interface or subsystem.
*   **User wants:** Know what depends on it and whether prior changes caused problems.
*   **Ideal outcome:** The answer combines structural impact with historical bug/refactor/rationale evidence.

### Use Case 4: PR Review Preparation

*   **Trigger:** A reviewer receives a PR touching unfamiliar files.
*   **User wants:** Quickly understand the touched area and relevant past decisions.
*   **Ideal outcome:** The reviewer sees linked history, claims, and risk notes before commenting.

### Use Case 5: AI-Agent Context Pack

*   **Trigger:** An engineer wants to use an AI coding agent on a complex repo.
*   **User wants:** Provide the agent with grounded context and constraints.
*   **Ideal outcome:** DevOnboard supplies cited context so the agent does not rely only on local snippets.

## Existing Alternatives

| Alternative | What it does well | Where it falls short |
|---|---|---|
| Manual grep / IDE search | Fast for known symbols and strings | Does not explain rationale or history |
| README / wiki | Good for curated overview | Often stale and incomplete |
| Git blame / git log | Finds who changed a line and when | Manual, fragmented, not semantic |
| GitHub PR search | Preserves discussion and review evidence | Hard to connect back to current code structure |
| Asking senior engineers | High-quality context | Interruptive, not scalable, knowledge disappears when people leave |
| Generic AI assistant | Fast natural-language answers | May hallucinate and often lacks citations or repo history |
| Code search products | Strong source lookup | Usually weaker on design rationale and refactor history |

## Your Wedge

DevOnboard combines code structure and development history into one cited graph, allowing engineers to ask how, why, and risk questions in the same workflow.

## References & Further Reading

*   Git documentation: https://git-scm.com/doc
*   GitHub REST API documentation: https://docs.github.com/rest
*   Google Cloud DORA Reports: https://cloud.google.com/devops/state-of-devops

**Keywords for Further Research:** developer onboarding, code search alternatives, git history search, refactor risk, repository intelligence
