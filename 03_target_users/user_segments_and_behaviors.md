# Target Users: Segments and Behaviors

## Primary User Segment

*   **Who they are:** New software engineers joining an existing repository, including new hires, interns, contractors, and open-source contributors.
*   **Goals:** Understand architecture quickly, make safe first changes, avoid repeated interruptions, and know where to inspect before editing.
*   **Pain points:** READMEs are incomplete, senior engineers are busy, PR history is hard to search, and AI answers lack citations.
*   **Current workarounds:** grep, GitHub search, `git blame`, reading old PRs, asking teammates, and prompting generic AI assistants with copied snippets.
*   **What they value:** Speed, trustworthy evidence, concrete file references, and clear next steps.

## Secondary User Segment

*   **Who they are:** Maintainers, tech leads, and senior engineers responsible for architecture and code review.
*   **Goals:** Preserve rationale, review changes faster, reduce onboarding burden, and prevent risky refactors.
*   **Pain points:** They repeatedly answer the same "why" questions and must reconstruct context from old commits during reviews.

## Behavioral Patterns & Trends

*   **Search-first behavior:** Engineers usually search before asking, so the product must support quick lookup and direct citations.
*   **Skepticism toward AI:** Developers may use AI daily but still distrust uncited answers for high-risk changes.
*   **Context switching:** Onboarding requires jumping between source files, PRs, issues, docs, and chat history.
*   **Time pressure:** New contributors want to become productive quickly, while maintainers want fewer review delays.

## A Day in Their Life

A new engineer is assigned a small refactor in an unfamiliar subsystem. They read the README, search for the interface name, inspect a few files, and ask an AI assistant for a summary. The answer sounds plausible, but it does not explain why the interface exists or whether previous refactors caused issues. They then spend another hour reading PRs and asking a senior teammate. DevOnboard should collapse that flow into one cited structural and historical answer.

## How They Currently Discover & Decide

*   They search GitHub, IDE symbols, commit history, and internal docs.
*   They trust senior engineers, tests, PR discussions, and concrete file references more than generic AI prose.
*   They decide to change code only after identifying likely blast radius and historical risk.

## References & Further Reading

*   GitHub Copilot productivity study: https://arxiv.org/abs/2302.06590
*   Google Cloud DORA Reports: https://cloud.google.com/devops/state-of-devops
*   Stack Overflow Developer Survey: https://survey.stackoverflow.co/

**Keywords for Further Research:** developer onboarding, code review behavior, AI trust, engineering knowledge sharing, refactor safety
