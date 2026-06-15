#!/usr/bin/env python3
"""Run 17 benchmark questions against the DevOnboard query system and collect answers."""

import json
import sys
import time
import httpx
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
OUTPUT_DIR = Path(__file__).parent.parent / "benchmark" / "results"
OUTPUT_FILE = OUTPUT_DIR / "17_questions_answers.json"
OUTPUT_MD = OUTPUT_DIR / "17_questions_answers.md"

QUESTIONS = [
    # Group 1 — Structural (single/few files, baseline)
    {
        "id": 1,
        "group": "Group 1 — Structural (single/few files, baseline)",
        "query": "List the 8 stages of GoClaw's agent pipeline in execution order, and identify the file(s) that define them.",
    },
    {
        "id": 2,
        "group": "Group 1 — Structural (single/few files, baseline)",
        "query": "Which function routes a tool call to the exec tool, and where is it located in internal/?",
    },
    {
        "id": 3,
        "group": "Group 1 — Structural (single/few files, baseline)",
        "query": "How does the 4-Mode Prompt System (Full/Task/Minimal/None) decide which mode to use for a given session?",
    },
    # Group 2 — Structural, multi-file / cross-package
    {
        "id": 4,
        "group": "Group 2 — Structural, multi-file / cross-package",
        "query": "Trace the full call flow from a WebSocket message arriving to the agent pipeline's context stage beginning execution.",
    },
    {
        "id": 5,
        "group": "Group 2 — Structural, multi-file / cross-package",
        "query": "How is the 3-Tier Memory system's progressive L0/L1/L2 loading implemented — which structs/interfaces are involved and in which files?",
    },
    {
        "id": 6,
        "group": "Group 2 — Structural, multi-file / cross-package",
        "query": "What methods does the ProviderAdapter interface define, and how many providers implement it? List each provider's file.",
    },
    # Group 3 — Impact analysis (many files at once)
    {
        "id": 7,
        "group": "Group 3 — Impact analysis (many files at once)",
        "query": "If I add a new method to the ProviderAdapter interface, which files would need to change? List all of them.",
    },
    {
        "id": 8,
        "group": "Group 3 — Impact analysis (many files at once)",
        "query": "What event types does the DomainEventBus handle, and which worker pools subscribe to which events? Show the relationships.",
    },
    # Group 4 — Historical / commit & PR specific
    {
        "id": 9,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "Why was the Knowledge Vault designed with [[wikilinks]] instead of standard foreign keys? Is there a commit or PR explaining this decision?",
    },
    {
        "id": 10,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "PR #950 is titled 'fix(security): close auth bypass + default-permit RBAC (issue #866)'. What was the original auth bypass vulnerability, which files did the fix touch, and what was the RBAC default-permit behavior before this fix?",
    },
    {
        "id": 11,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "PR #937 fixed an SSRF issue in TTS test-connection validation (fix(http): validate tts test-connection api_base with provider SSRF guard). What was the attack vector, and which provider adapter(s) were affected?",
    },
    {
        "id": 12,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "Migration 000056 adds a chat_id column to vault tables for isolated-team isolation. What problem did this solve — was there a prior bug report or design discussion about vault data leaking across teams?",
    },
    {
        "id": 13,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "PR #901 mentions 'Gemini ACP protocol fixes and multi-session architecture.' What was broken in the original Gemini ACP implementation, and how does the new multi-session architecture differ from the old one?",
    },
    {
        "id": 14,
        "group": "Group 4 — Historical / commit & PR specific",
        "query": "PR #949 excludes node deps and dist from the Docker build context. What was the original problem this caused — larger image size, build failures, or something else? Find the discussion or commit message that explains it.",
    },
    # Group 5 — Hybrid (structural + historical combined)
    {
        "id": 15,
        "group": "Group 5 — Hybrid (structural + historical combined)",
        "query": "I want to refactor the KnowledgeVault search interface to support an additional search backend. List all current callers (structural), and tell me whether there's been any past discussion or issue about changing the search backend (historical).",
    },
    {
        "id": 16,
        "group": "Group 5 — Hybrid (structural + historical combined)",
        "query": "The Self-Evolution pipeline (metrics → suggestions → auto-adapt) has guardrails preventing agents from changing their identity. Was there ever a version without these guardrails, or an incident/PR that led to adding them?",
    },
    {
        "id": 17,
        "group": "Group 5 — Hybrid (structural + historical combined)",
        "query": "Is it safe to modify the RBAC permission resolution logic touched by PR #950? Show both the current callers of that logic (structural) and any related security issues filed before or after that PR (historical).",
    },
]


def query_stream(query: str, mode: str = "auto", timeout: float = 120.0) -> dict:
    """Send a query to the streaming endpoint and collect the full response."""
    result = {
        "answer": "",
        "route": mode,
        "citations": [],
        "warnings": [],
    }
    start_time = time.time()
    try:
        with httpx.stream(
            "POST",
            f"{BACKEND_URL}/query/stream",
            json={
                "query": query,
                "mode": mode,
                "node_ids": [],
                "allow_external_llm_for_private_repo": True,
            },
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                parts = buffer.split("\n\n")
                buffer = parts[-1]
                for part in parts[:-1]:
                    if not part.strip():
                        continue
                    event_type = ""
                    data_str = ""
                    for line in part.split("\n"):
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            data_str = line[5:].strip()
                    if not event_type or not data_str:
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if event_type == "route":
                        result["route"] = data.get("route", mode)
                    elif event_type == "citations":
                        result["citations"] = data.get("citations", [])
                    elif event_type == "warnings":
                        result["warnings"] = data.get("warnings", [])
                    elif event_type == "token":
                        result["answer"] += data.get("token", "")
    except Exception as e:
        result["answer"] = f"ERROR: {e}"
        result["warnings"].append(str(e))

    result["elapsed_s"] = round(time.time() - start_time, 2)
    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = []

    total = len(QUESTIONS)
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{total}] Q{q['id']}: {q['query'][:80]}...")
        print(f"  Group: {q['group']}")
        print(f"  Querying...", end="", flush=True)

        result = query_stream(q["query"])
        print(f" done in {result['elapsed_s']}s")
        print(f"  Route: {result['route']}")
        print(f"  Answer length: {len(result['answer'])} chars")
        print(f"  Citations: {len(result['citations'])}")
        if result["warnings"]:
            print(f"  Warnings: {result['warnings']}")

        all_results.append({
            "id": q["id"],
            "group": q["group"],
            "query": q["query"],
            "route": result["route"],
            "answer": result["answer"],
            "citations": result["citations"],
            "warnings": result["warnings"],
            "elapsed_s": result["elapsed_s"],
        })

        # Small delay between questions to avoid rate limiting
        if i < total:
            time.sleep(1)

    # Save JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON results saved to {OUTPUT_FILE}")

    # Save Markdown
    with open(OUTPUT_MD, "w") as f:
        f.write("# DevOnboard — 17 Questions Benchmark Results\n\n")
        f.write(f"**Generated at**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        current_group = ""
        for r in all_results:
            if r["group"] != current_group:
                current_group = r["group"]
                f.write(f"## {current_group}\n\n")

            f.write(f"### Q{r['id']}: {r['query']}\n\n")
            f.write(f"**Route**: `{r['route']}` | **Time**: {r['elapsed_s']}s | "
                    f"**Citations**: {len(r['citations'])}\n\n")
            if r["warnings"]:
                f.write(f"> ⚠️ Warnings: {'; '.join(r['warnings'])}\n\n")
            f.write(f"**Answer:**\n\n{r['answer']}\n\n")
            if r["citations"]:
                f.write("**Citations:**\n\n")
                for c in r["citations"]:
                    label = c.get("label", c.get("node_id", "unknown"))
                    ctype = c.get("type", "")
                    summary = c.get("summary", "")
                    f.write(f"- `[{ctype}]` **{label}**: {summary[:120]}\n")
                f.write("\n")
            f.write("---\n\n")

    print(f"✅ Markdown results saved to {OUTPUT_MD}")


if __name__ == "__main__":
    main()
