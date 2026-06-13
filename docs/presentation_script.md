# DevOnboard Presentation & Demo Script

This script provides a structured guide for presenting **DevOnboard**. It is divided into slides/topics, speaker notes, and live system actions.

---

## Part 1: The Hook & The Problem (Duration: 2 Minutes)

### Speaker Notes
*   "Hello everyone. Today, I want to talk about one of the most expensive bottlenecks in software engineering: **onboarding and context loss**."
*   "When a new engineer joins a team, or when you are asked to refactor an unfamiliar module, what is the first thing you do? You open the files, read the code, and try to understand *what* it does."
*   "But code only explains the *what*—it never explains the *why*. The design rationale, the tradeoffs made, the rejected alternatives, and the refactoring risks are scattered across commit histories, PR reviews, issue trackers, and senior engineers' heads."
*   "As a result, onboarding is slow, code reviews are bottlenecks, and AI coding assistants frequently hallucinate because they lack codebase-specific institutional memory."
*   "That is why we built **DevOnboard**—an AI-powered codebase onboarding assistant with cited institutional memory."

---

## Part 2: Product Solution & High-Level Architecture (Duration: 3 Minutes)

### Speaker Notes
*   "DevOnboard doesn't just read code files. It scans the repository structure, ingests Git development history, and extracts architectural tradeoffs using the Gemini API."
*   "All of this information is compiled into a local, durable **Knowledge Graph** stored as a simple JSON file."
*   "This knowledge graph contains two types of nodes:"
    1.  **Structural Nodes**: representing files, modules, classes, and functions.
    2.  **Historical Nodes**: representing authors, Git commits, PR reviews, and AI-extracted design claims."
*   "When you query the system, it uses **Graph-First Hybrid Retrieval (RAG)**. Instead of doing a simple semantic search that pulls random text, DevOnboard traverses calling and import relationships, hops onto Git commits, retrieves the associated design decisions, and synthesizes an answer with direct inline citations linked back to raw commits and source code."

---

## Part 3: Live Walkthrough & Demo (Duration: 5 Minutes)

### Step 1: Initialize and Scan
*   **Action**: Show the top navigation bar of the UI.
*   **Script**: 
    > "Let's see the product in action. We have configured DevOnboard to run against a target repository—in this case, an open-source Go project called `goclaw`. Currently, no graph is loaded."
*   **Action**: Click the **Run Scan** button.
*   **Script**:
    > "I'll click **Run Scan**. Behind the scenes, the FastAPI backend traverses the repository, extracts modules, imports, files, and functions, and compiles them into structural graph nodes. Now, in the left panel, you can see our file tree structure has populated."

### Step 2: Ingest Git History & Extract Rationale
*   **Action**: Click the **Ingest History** button.
*   **Script**:
    > "Next, I'll click **Ingest History**. The backend is running a Git log parser to extract commits, dates, and authors. But more importantly, it feeds the commit messages and PR logs to Gemini to extract explicit design tradeoffs."
    > "Gemini filters out the noise—like 'fixed typo' or 'minor cleanup'—and extracts only real architectural decisions, such as why a certain database adaptor was chosen, saving them as design claims."

### Step 3: Inspecting History (The "Why" Inspector)
*   **Action**: Click on a file in the left panel (e.g., `ProviderAdapter` or `internal/providers/adapter.go`).
*   **Script**:
    > "Now that ingestion is complete, let's click on a file in the left-hand navigation. Instantly, on the right panel—our **History and Why Inspector**—we see the entire context of this file."
    > "We see who wrote it, the Git commits that touched it, and the exact design claims extracted from the commit history. We can see *why* this adapter was split from the main pipeline without having to dig through GitHub manually."

### Step 4: Asking a Cited Onboarding Question
*   **Action**: Click on one of the suggested demo queries (e.g., *"Why was progressive memory loading chosen?"* or *"Is it safe to refactor ProviderAdapter?"*) and submit it.
*   **Script**:
    > "Let's ask a question: *'Is it safe to refactor ProviderAdapter?'*"
    > "Watch the center panel. The system classifies the route as 'hybrid', finds the adapter node, traverses its structural dependencies to see what might break, retrieves historical design claims, and synthesizes a response."
    > "Notice the citations in the answer. Every statement has a clickable node tag like `[source:commit:a3f2b1]`. If I click on it, it highlights the exact historical evidence. This completely eliminates AI hallucinations because the user can verify every single claim."

### Step 5: Generating Evidence Packs
*   **Action**: Click the **Generate Pack** button in the UI.
*   **Script**:
    > "If you are preparing a Pull Request or onboarding an AI coding agent to write code for you, you need a quick context pack. By clicking **Generate Pack**, DevOnboard compiles a structured Markdown document."
    > "It highlights the changed scope, structural blast radius, historical constraints, and warnings of what *not* to assume. This is ready to be pasted directly into a PR description or fed to an autonomous coding agent."

---

## Part 4: Evaluation & Benchmarks (Duration: 2 Minutes)

### Speaker Notes
*   **Action**: Click on the **Benchmark** link to open the dashboard.
*   **Script**:
    > "How do we know this retrieval is better than standard LLMs? We built a dedicated **Benchmark Dashboard**."
    > "Here, we run standardized onboarding queries. We compare DevOnboard—which uses our graph retrieval—against a 'Plain Agent' which only has access to the README and a file listing."
    > "We measure latency, citation coverage, and a computed **Evidence Usefulness Score** on a scale of 1 to 5. As you can see, DevOnboard consistently achieves higher citation rates and usefulness scores because it anchors the LLM with direct historical and structural relationships."

---

## Part 5: Design Decisions & Wrap-Up (Duration: 2 Minutes)

### Speaker Notes
*   "To wrap up, here are the key architectural decisions that make DevOnboard reliable:"
    1.  **JSON Graph Primary Artifact**: The graph is persisted as a readable JSON file. It is easy to audit, diff, and migrate.
    2.  **Conservative Rationale Extraction**: We strictly enforce that a claim must have source evidence. If the AI cannot find explicit proof, no claim is created.
    3.  **Graph-First, Vector-Second**: Direct dependencies and Git history links always outrank semantic vector similarity, preserving true provenance.
*   "With DevOnboard, we turn fragmented developer history into a machine-readable, cited knowledge base. Thank you, and I am happy to take any questions."
