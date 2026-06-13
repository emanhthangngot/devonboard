# Case Study: Git Blame And Pull Request History As Developer Memory

## 1. Problem Statement

Developers often use `git blame`, commit history, and pull request discussions to reconstruct why code changed. These tools preserve evidence, but the workflow is manual and fragmented.

## 2. Target Personas & User Research

*   **Primary persona:** Maintainers investigating old code before changing it.
*   **Secondary persona:** New contributors trying to understand project conventions and design history.

**Key Pain Points Solved:**

*   `git blame` identifies a commit but not the full decision chain.
*   PR discussions are hard to search semantically.
*   Related issues, reviews, and commits are scattered.

## 3. The Solution

Git and GitHub history provide raw institutional memory. A better product can convert that raw evidence into linked nodes, claims, and refactor-risk context.

### The Mechanisms

1.  Link files/functions to commits that changed them.
2.  Resolve commits to PRs, issues, and review comments.
3.  Extract rationale and rejected alternatives into searchable claims.

## 4. Impact and Success Metrics

*   **Time to rationale:** How quickly an engineer can answer "why was this built this way?"
*   **Evidence coverage:** Percentage of important nodes with linked historical evidence.
*   **Refactor confidence:** Whether maintainers can identify risk before editing.

## 5. Lifecycle of the Feature & Lessons Learnt

*   **How it started:** Git history was created for version control, not onboarding.
*   **Key insight / pivot:** The same history can become a product data layer when linked to current code structure.
*   **Lesson for us:** DevOnboard should turn existing development artifacts into an inspectable graph instead of asking teams to write perfect documentation.

## References & Further Reading

*   Git documentation: https://git-scm.com/doc
*   GitHub REST API documentation: https://docs.github.com/rest

**Keywords for Further Research:** git blame, pull request history, design rationale, software archaeology
