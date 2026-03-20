import json
import os
from enum import Enum

from noidea.git import get_git_root

config_dir = os.path.expanduser("~/.noidea")
config_path = os.path.expanduser("~/.noidea/config.json")
keys_path = os.path.expanduser("~/.noidea/keys.json")

DEFAULTS = {
    "llm": {
        "max_tokens": 1024,
        "small_model": "claude-haiku-4-5",
        "large_model": "claude-sonnet-4-6",
        "context_limit": 600000,
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


class Provider(str, Enum):
    ANTHROPIC = "anthropic"


def deep_merge(base, override):
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(value, dict) and isinstance(result[key], dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_config() -> dict:
    config = DEFAULTS

    if os.path.exists(config_path):
        with open(config_path) as f:
            config = deep_merge(config, json.load(f))

    repo_root = get_git_root()
    if repo_root:
        repo_config_path = os.path.join(repo_root, ".noidea", "config.json")
        if os.path.exists(repo_config_path):
            with open(repo_config_path) as f:
                config = deep_merge(config, json.load(f))

    return config


def initialize():
    os.makedirs(config_dir, exist_ok=True)

    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump(DEFAULTS, f, indent=2)

    if not os.path.exists(keys_path):
        with open(keys_path, "w") as f:
            json.dump([], f)


def save_key(name: str):
    with open(keys_path) as f:
        keys = json.load(f)
    if name in keys:
        return False
    keys.append(name)
    with open(keys_path, "w") as f:
        json.dump(keys, f)
    return True


def remove_key(name: str):
    with open(keys_path) as f:
        keys = json.load(f)
    if name not in keys:
        return False
    keys.remove(name)
    with open(keys_path, "w") as f:
        json.dump(keys, f)
    return True


def list_keys() -> list:
    with open(keys_path) as f:
        return json.load(f)
