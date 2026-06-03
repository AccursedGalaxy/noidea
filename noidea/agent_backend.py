"""Invoke the driver-os agent as a commit-message backend, as a subprocess.

The agent is a separate Go binary (cmd/commit-msg in driver-os): it reads the staged diff, the
repo's conventions, and the changed files over a few turns, then prints a commit message and
writes its full reasoning trace to RUN_LOG_FILE. We shell out to it — language-agnostic, and the
agent owns its own sandbox — rather than embedding it. Every failure path returns None so the
caller falls back to the fast single-shot generator: an unavailable or broken agent must never
block a commit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

from rich.console import Console

from noidea.config import LlmConfig
from noidea.key_store import key_store

# Notices go to stderr; stdout is reserved for the commit message the hook/CI consumes.
console = Console(stderr=True)

# The canonical name of the driver-os commit-msg binary on PATH, used when neither the config
# nor the env var names an explicit path.
_DEFAULT_BINARY_NAME = "driver-os-commit-msg"
_BINARY_ENV = "NOIDEA_AGENT_BIN"

# The agent is multi-turn; give it real headroom but a hard ceiling so a hung run still falls
# back to the fast path rather than wedging a commit.
_AGENT_TIMEOUT_SECONDS = 120


def resolve_binary(cfg: LlmConfig) -> str | None:
    """Find the agent binary: explicit config path, then env override, then PATH lookup."""
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    candidate = cfg.agent_binary or os.environ.get(_BINARY_ENV, "")
    if candidate:
        # An explicit path must actually be runnable; a typo should surface, not silently
        # fall through to a PATH lookup that finds a different binary.
        return (
            candidate
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK)
            else None
        )
    found = shutil.which(_DEFAULT_BINARY_NAME)
    assert found is None or isinstance(found, str), "which must return a path or None"
    return found


def generate_with_agent(
    repo_root: str,
    diff: str,
    branch: str,
    staged_files: list[str],
    run_file: str,
    cfg: LlmConfig,
) -> str | None:
    """Run the agent on the staged diff and return its message, or None to fall back.

    Sets RUN_LOG_FILE to ``run_file`` so the agent's full trace lands in the dogfood record the
    reconcile step later annotates with the human verdict. None is returned (with a stderr
    notice) for every failure: binary absent, no OpenRouter key, non-zero exit, or timeout.
    """
    assert isinstance(repo_root, str) and repo_root, (
        "repo_root must be a non-empty string"
    )
    assert isinstance(diff, str) and diff.strip(), "diff must be a non-empty string"
    binary = resolve_binary(cfg)
    if binary is None:
        console.print(
            "[dim]agent backend: binary not found — set llm.agent_binary; falling back.[/dim]"
        )
        return None
    api_key = key_store.get("openrouter")
    if not api_key:
        console.print(
            "[dim]agent backend: no OpenRouter key — run 'noidea keys add'; falling back.[/dim]"
        )
        return None

    payload = json.dumps({"diff": diff, "branch": branch, "staged_files": staged_files})
    env = _agent_env(api_key, run_file, cfg)
    # The binary writes its trace to run_file via os.WriteFile, which does not create parents.
    os.makedirs(os.path.dirname(run_file), exist_ok=True)
    try:
        result = subprocess.run(
            [binary],
            input=payload,
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=_AGENT_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as error:
        console.print(f"[dim]agent backend: {error}; falling back.[/dim]")
        return None

    message = result.stdout.strip()
    if result.returncode == 0 and message:
        return message
    # A failed run is informative, not fatal: surface a short reason and fall back.
    reason = (
        result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "no output"
    )
    console.print(
        f"[dim]agent backend: exit {result.returncode} ({reason}); falling back.[/dim]"
    )
    return None


def _agent_env(api_key: str, run_file: str, cfg: LlmConfig) -> dict:
    """Build the agent subprocess environment: inherit, then set the key, model, and trace path."""
    assert isinstance(api_key, str) and api_key, "api_key must be a non-empty string"
    assert isinstance(run_file, str) and run_file, "run_file must be a non-empty string"
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = api_key
    env["OPENROUTER_MODEL"] = cfg.agent_model
    env["RUN_LOG_FILE"] = run_file
    return env
