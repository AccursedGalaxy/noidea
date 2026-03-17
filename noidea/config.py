import json
import os
import tomllib

config_path = os.path.expanduser("~/.noidea/noidea.toml")
keys_path = os.path.expanduser("~/.noidea/keys.json")


def load_config() -> dict:
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config
    else:
        defaults = {
            "llm": {
                "max_tokens": 1024,
                "model": "claude-sonnet-4-6",
                "system_prompt": (
                    "Generate a concise git commit message from the provided diff.\n"
                    "Rules:\n"
                    "- First line: imperative mood, max 72 chars, no period\n"
                    "- If needed, blank line then body explaining *why*, not *what*\n"
                    "- Use conventional commits prefix if scope is clear (feat/fix/refactor/chore/docs/test)\n"
                    "- No filler, no praise, no explanation outside the commit message itself\n"
                    "Output only the commit message. No code block!"
                ),
            }
        }

        return defaults


def save_key(name: str):
    if os.path.exists(keys_path):
        with open(keys_path) as f:
            keys = json.load(f)
    else:
        keys = []

    keys.append(name)
    with open(keys_path, "w") as f:
        json.dump(keys, f)


def remove_key(name: str):
    if os.path.exists(keys_path):
        with open(keys_path) as f:
            keys = json.load(f)
    else:
        return

    keys.remove(name)
    with open(keys_path, "w") as f:
        json.dump(keys, f)


def list_keys():
    if os.path.exists(keys_path):
        with open(keys_path) as f:
            keys = json.load(f)
        print(keys)
    else:
        print("no keys saved yet.")
