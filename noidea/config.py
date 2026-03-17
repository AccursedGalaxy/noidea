import os
import tomllib

config_path = os.path.expanduser("~/.noidea/noidea.toml")


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
                "system_prompt": "write a commit message",
            }
        }

        return defaults
