---
name: Commit feedback should be a standalone command
about: Make AI feedback opt-in and remove the extra LLM call from the commit workflow
labels: enhancement
---

## Problem
Right now, noidea can trigger *two* LLM calls in a typical commit workflow:
1) `prepare-commit-msg` hook: generate commit message suggestion
2) `post-commit` hook: run `noidea moai` with AI feedback enabled

The post-commit AI feedback adds latency and breaks flow. The feedback is nice sometimes, but it should be **opt-in**.

## Desired behavior
- Keep **one** LLM call on `git commit` to generate the commit message suggestion.
- Make commit feedback a **standalone command** the user runs when they want it (e.g. `noidea moai --ai`).

## Acceptance criteria
- `noidea init` no longer installs a post-commit hook that conditionally triggers an AI call.
- Existing users can still get feedback via a manual command.
- Docs updated to reflect the new workflow.
