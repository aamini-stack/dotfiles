# aamini coding

This document outlines global rules for Aria's agents to follow.

## Rules

1. **DO NOT USE GIT**. Prefer the jujutsu (jj) version control system.
2. When making technical decisions, do not give much weight to development cost.
   Instead, prefer quality, simplicity, robustness, scalability, and long-term
   maintanability.
3. Never write comments that restate what the code already says — if a comment
   explains *what* the code does, delete it and rename or restructure the code
   instead. Comments must add information the code cannot express. Allowed:

   - **Critical context** — why a non-obvious decision was made, constraints
     imposed by external systems, or links to reference material.
   - **Section markers** — short labels (often one word) like `// Shared`, or
     the banner style `// ===== Section =====`, to annotate blocks of code.

## Agent skills

### Issue tracker

Issues are tracked as GitHub issues on this repo, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary — label strings equal the five canonical roles (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
