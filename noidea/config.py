import json
import os
from enum import Enum

config_dir = os.path.expanduser("~/.noidea")
config_path = os.path.expanduser("~/.noidea/config.json")
keys_path = os.path.expanduser("~/.noidea/keys.json")

DEFAULTS = {
    "llm": {
        "max_tokens": 1024,
        "model": "claude-sonnet-4-6",
        "system_prompt": (
            "Generate a concise git commit message from the provided diff.\n"
            "Rules:\n"
            "- First line: imperative mood, max 72 chars, no period\n"
            "- Second line: blank line\n"
            "- Third line and below: body explaining *why*, not *what*\n"
            "- Use conventional commits prefix if scope is clear (feat/fix/refactor/chore/docs/test)\n"
            "- No filler, no praise, no explanation outside the commit message itself\n"
            "Output only the commit message. No code block!"
        ),
    }
}


class Provider(str, Enum):
    ANTHROPIC = "anthropic"


def load_config() -> dict:
    with open(config_path) as f:
        return json.load(f)


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
