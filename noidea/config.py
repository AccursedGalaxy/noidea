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
            "Generate a git commit message from the provided diff, branch name, and staged file list.\n"
            "Subject line rules:\n"
            "- Imperative mood, max 72 chars, no period\n"
            "- Use conventional commits prefix (feat/fix/refactor/chore/docs/test)\n"
            "- Describe the single intent behind the change, not what files were touched\n"
            "- Use the branch name to infer intent when possible\n"
            "- Avoid generic verbs like 'update' or 'add' — be specific\n"
            "- Never use 'and' to combine multiple changes — pick the overarching purpose\n"
            "Body rules:\n"
            "- Optional — only include if the *why* is non-obvious from the subject\n"
            "- Explain *why* the change was made, not *what* changed (the diff shows what)\n"
            "- Max 2-3 sentences\n"
            "Output only the commit message, no markdown formatting."
        ),
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
