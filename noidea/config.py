"""Three-tier configuration: built-in defaults, user overrides, repo overrides."""

import json
import os
import sys
from enum import Enum

from noidea.git import get_git_root

SERVICE_NAME = "noidea"
CONFIG_DIR_NAME = ".noidea"
CONFIG_FILENAME = "config.json"
KEYS_FILENAME = "keys.json"

CONFIG_DIR = os.path.expanduser(f"~/{CONFIG_DIR_NAME}")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILENAME)
KEYS_PATH = os.path.join(CONFIG_DIR, KEYS_FILENAME)

DEFAULTS = {
    "llm": {
        "max_tokens": 1024,
        "small_model": "claude-haiku-4-5",
        "large_model": "claude-sonnet-4-6",
        "context_limit": 600000,  # Character threshold for model selection, not a token limit.
        "system_prompt": (
            "Generate a commit message from the diff, branch name, and staged files.\n"
            "Subject: imperative mood, max 72 chars, no period, conventional commits format (e.g. feat(scope): ..., fix(scope): ...).\n"
            "One intent per subject — no 'and'. Use branch name to infer purpose.\n"
            "Prefer specific verbs over generic ones (update, add, remove).\n"
            "Body: only if the why or scope is non-obvious. Use bullet points for multi-change commits, one action per bullet. Keep each line under 72 chars. No fluff.\n"
            "Output only the raw commit message."
        ),
        "temperature": 1.0,
    }
}


_LLM_SCHEMA = {
    "max_tokens": int,
    "small_model": str,
    "large_model": str,
    "context_limit": (int, float),
    "system_prompt": str,
    "temperature": (int, float),
}


class Provider(str, Enum):
    ANTHROPIC = "anthropic"


def validate_config(config: dict) -> dict:
    """Check config types after merge. Replace bad values with defaults."""
    llm = config.get("llm")
    if not isinstance(llm, dict):
        print(
            "Warning: config 'llm' section is not a dict, using defaults.",
            file=sys.stderr,
        )
        return DEFAULTS.copy()

    for key, expected_type in _LLM_SCHEMA.items():
        value = llm.get(key)
        if not isinstance(value, expected_type):
            print(
                f"Warning: llm.{key} has wrong type"
                f" ({type(value).__name__}), using default.",
                file=sys.stderr,
            )
            llm[key] = DEFAULTS["llm"][key]

    return config


def deep_merge(base, override):
    # Iterative stack-based merge to guarantee bounded execution depth.
    result = base.copy()
    stack = [(result, override)]

    while stack:
        target, source = stack.pop()
        for key, value in source.items():
            if (
                key in target
                and isinstance(value, dict)
                and isinstance(target[key], dict)
            ):
                target[key] = target[key].copy()
                stack.append((target[key], value))
            else:
                target[key] = value

    return result


def load_config() -> dict:
    config = DEFAULTS

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                config = deep_merge(config, json.load(f))
        except (OSError, json.JSONDecodeError) as error:
            # Warn instead of crashing: a corrupt config should not block all CLI usage.
            print(f"Warning: could not load {CONFIG_PATH}: {error}", file=sys.stderr)

    repo_root = get_git_root()
    if repo_root:
        repo_config_path = os.path.join(repo_root, CONFIG_DIR_NAME, CONFIG_FILENAME)
        if os.path.exists(repo_config_path):
            try:
                with open(repo_config_path) as f:
                    # Repo config merges last so project-specific settings win.
                    config = deep_merge(config, json.load(f))
            except (OSError, json.JSONDecodeError) as error:
                print(
                    f"Warning: could not load {repo_config_path}: {error}",
                    file=sys.stderr,
                )

    config = validate_config(config)
    return config


def initialize():
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except OSError as error:
        print(f"Warning: could not create {CONFIG_DIR}: {error}", file=sys.stderr)
        return

    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULTS, f, indent=2)
        except OSError as error:
            print(f"Warning: could not write {CONFIG_PATH}: {error}", file=sys.stderr)

    if not os.path.exists(KEYS_PATH):
        try:
            with open(KEYS_PATH, "w") as f:
                json.dump([], f)
        except OSError as error:
            print(f"Warning: could not write {KEYS_PATH}: {error}", file=sys.stderr)


def save_key(name: str):
    with open(KEYS_PATH) as f:
        keys = json.load(f)
    if name in keys:
        return False
    keys.append(name)
    with open(KEYS_PATH, "w") as f:
        json.dump(keys, f)
    return True


def remove_key(name: str):
    with open(KEYS_PATH) as f:
        keys = json.load(f)
    if name not in keys:
        return False
    keys.remove(name)
    with open(KEYS_PATH, "w") as f:
        json.dump(keys, f)
    return True


def list_keys() -> list:
    with open(KEYS_PATH) as f:
        return json.load(f)
