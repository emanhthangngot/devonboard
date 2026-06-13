# Case Study: Sourcegraph Cody And Repository-Aware Code Search

## 1. Problem Statement

Developers working in large codebases cannot rely on file-by-file reading alone. They need fast search, cross-repository context, and answers grounded in actual code. Traditional keyword search helps locate files but does not always explain architecture or historical reasoning.

## 2. Target Personas & User Research

*   **Primary persona:** Professional software engineers working in large or unfamiliar repositories.
*   **Secondary persona:** Engineering leads and platform teams responsible for developer productivity.

**Key Pain Points Solved:**

*   Finding relevant code across large repositories is slow.
*   Generic AI answers are less useful without repository-specific context.
*   Engineers need links back to source code to trust generated explanations.

## 3. The Solution

Repository-aware code search and AI assistants combine indexed code search with natural-language answers. The strongest pattern for DevOnboard is not just "chat with code", but evidence-grounded explanations that keep users connected to source artifacts.

### The Mechanisms

1.  Index repository content so lookup is fast.
2.  Retrieve relevant code context before answer generation.
3.  Present answers with references back to source files.

## 4. Impact and Success Metrics

*   **Search latency:** Developers expect code lookup to feel near-instant after indexing.
*   **Citation coverage:** Useful code explanations link back to source files or symbols.
*   **Task completion:** The product should reduce time spent manually tracing files and asking teammates.

## 5. Lifecycle of the Feature & Lessons Learnt

*   **How it started:** Code search became a core developer workflow before AI chat became mainstream.
*   **Key insight / pivot:** AI is more useful when paired with retrieved repository context and citations.
*   **Lesson for us:** DevOnboard should keep evidence visible and make history/rationale first-class, not hidden behind a chat response.

## References & Further Reading

*   Sourcegraph: https://sourcegraph.com/
*   GitHub Copilot productivity study: https://arxiv.org/abs/2302.06590

**Keywords for Further Research:** repository-aware AI, code search, source citations, developer productivity
