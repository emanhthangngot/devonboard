# DevOnboard Cost Analysis

This document outlines the operational and API cost structure of running **DevOnboard** in local development, team, and enterprise scenarios.

---

## 1. Core Cost Structure: $0 (Free/Open Source by Default)

The default configuration of DevOnboard runs **entirely locally** and utilizes open-source components, meaning the baseline operational cost is **zero**.

| Component | Technology | Cost | Reason |
|---|---|---|---|
| **Development Stack** | Python, FastAPI, Next.js | **$0** | MIT/Apache open-source frameworks. |
| **Primary Graph Database** | Local JSON File | **$0** | Persisted directly to disk, requiring no commercial graph database license (e.g., Neo4j Aura). |
| **Secondary Indexes** | SQLite, Qdrant (Docker) | **$0** | Uses open-source local databases; no hosting or subscription fees. |
| **Ingestion Pipeline** | Git CLI | **$0** | Local Git operations do not consume API credits or bandwidth fees. |

---

## 2. LLM API Cost Structure (Gemini API)

DevOnboard uses the **Gemini API** (from Google AI Studio) for query routing, rationale extraction, and grounded answer synthesis.

### Option A: Free Tier (Google AI Studio)
*   **Cost**: **$0**
*   **Suitability**: Perfect for development, hackathons, personal usage, and small teams.
*   **Limits**: Google AI Studio provides a free rate limit (e.g., 15 RPM / 1 million TPM for Gemini 1.5 Flash), which is more than sufficient for running scans and answering questions on a local codebase.

### Option B: Pay-As-You-Go / Production Tier
If deployed at scale within an enterprise where the free tier limits are exceeded, billing is per-token (prices based on Gemini 1.5 Flash):
*   **Input Tokens**: ~$0.075 / 1 million tokens
*   **Output Tokens**: ~$0.30 / 1 million tokens

#### Graph-First Token Efficiency
DevOnboard is significantly more cost-efficient than generic RAG systems because of its **Graph-First hybrid retrieval**:
*   **Generic AI Assistant**: Feeds entire source files or directories into the LLM context window to answer questions (often 50,000 to 200,000 tokens per query). Cost: **$0.015 - $0.05 per query**.
*   **DevOnboard**: Filters and extracts only the top 3 structural nodes and top 5 historical evidence items (claims/commits). The context window sent to Gemini is extremely small (typically **under 4,000 tokens** per query). Cost: **$0.0003 per query** (virtually negligible).

---

## 3. GitHub API Costs
*   **Cost**: **$0**
*   **Limits**:
    *   *Unauthenticated*: 60 requests/hour limit.
    *   *Authenticated (using a free GitHub Personal Access Token)*: 5,000 requests/hour limit. DevOnboard parses git commits locally using the Git CLI, saving GitHub API requests for optional PR/issue comments.

---

## 4. Total Cost Summary

| Scenario | Setup Cost | Monthly Operating Cost | Cost Per Query |
|---|---|---|---|
| **Local Hackathon / Individual Dev** | $0 | **$0** (Free Gemini API Key) | **$0** |
| **Small Engineering Team (10 Devs)** | $0 | **$0** (Local/Shared Docker run) | **$0 - $2.00 / month** (depending on Gemini volume) |
| **Enterprise Deployment (100+ Devs)** | $0 | **$50 - $100 / month** (Optional cloud hosting for Qdrant/FastAPI) | **~$10 - $20 / month** (Total team Gemini token fees) |
