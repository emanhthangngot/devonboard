# Problem Statement

## Problem

Software teams lose codebase memory because source code explains what exists, but not why it was designed that way. New engineers must reconstruct context from scattered commits, PRs, issues, reviews, and conversations before they can safely change unfamiliar modules.

This is especially painful for fast-moving teams where onboarding is frequent, senior engineers are overloaded, and historical design decisions are not captured in current docs.

## Target Users

- Junior and newly joined engineers who need trustworthy context before editing unfamiliar code.
- Tech leads and reviewers who need faster ways to surface historical risk before approving changes.
- AI-agent users who need compact, cited context packs instead of raw, unsupported repository dumps.

## Current Workarounds

- Reading stale README/wiki pages.
- Searching GitHub, `git log`, and `git blame` manually.
- Asking senior engineers repetitive questions.
- Feeding broad code snippets into general AI tools and manually checking for hallucinations.

## Product Opportunity

DevOnboard can turn a local repository and its development history into a cited institutional-memory graph. The product should help users answer:

- how a subsystem works;
- why important code was designed that way;
- which commits, PRs, issues, or reviews support the answer;
- what risks matter before refactoring;
- what evidence should be included in a PR review or AI-agent context pack.

## Success Criteria

- A user can load the prepared demo repository and reach the first cited answer from the local web UI within 60 seconds after setup.
- Historical rationale is never shown without source evidence.
- Private or proprietary repository data is not sent to an external LLM unless the user explicitly opts in.
- Benchmark output demonstrates DevOnboard's citation and evidence coverage against a plain-agent baseline.
