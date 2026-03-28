import json
import os

import keyring
import keyring.errors
from rich.console import Console

from noidea import __version__
from noidea.config import CONFIG_PATH, SERVICE_NAME, list_keys, load_config
from noidea.git import HOOK_NAME, get_git_root, get_hooks_dir

console = Console(stderr=True)

OK = "[green]\u2713[/green]"
FAIL = "[red]\u2717[/red]"


def _check_repository():
    repo_root = get_git_root()
    if repo_root:
        console.print(f"Repository:     {OK} git repo detected")
    else:
        console.print(f"Repository:     {FAIL} not a git repository")


def _check_hook():
    hooks_dir = get_hooks_dir()
    if not hooks_dir:
        console.print(f"Hook:           {FAIL} {HOOK_NAME} not found")
        return

    hook_path = os.path.join(hooks_dir, HOOK_NAME)
    if not os.path.exists(hook_path):
        console.print(f"Hook:           {FAIL} {HOOK_NAME} not found")
        return

    try:
        with open(hook_path) as f:
            content = f.read()
    except OSError:
        console.print(f"Hook:           {FAIL} could not read {HOOK_NAME}")
        return

    if SERVICE_NAME in content:
        console.print(f"Hook:           {OK} {HOOK_NAME} installed ({hooks_dir})")
    else:
        console.print(
            f"Hook:           [yellow]![/yellow] {HOOK_NAME} exists"
            f" but not managed by {SERVICE_NAME}"
        )


def _check_config() -> tuple[dict, dict]:
    config = load_config()
    llm = config["llm"]
    if os.path.exists(CONFIG_PATH):
        console.print(f"Config:         {OK} {CONFIG_PATH} loaded")
    else:
        console.print("Config:         [dim]using defaults[/dim]")
    return config, llm


def _check_api_keys():
    try:
        keys = list_keys()
        if keys:
            for key in keys:
                stored = keyring.get_password(SERVICE_NAME, key)
                if stored:
                    console.print(f"API Key:        {OK} {key} (keyring)")
                else:
                    console.print(
                        f"API Key:        {FAIL} {key} registered but missing from keyring"
                    )
        else:
            console.print(f"API Key:        {FAIL} no key found (run 'noidea keys add')")
    except (OSError, json.JSONDecodeError, keyring.errors.KeyringError):
        console.print(f"API Key:        {FAIL} could not read keys")


def status():
    """Check if everything's wired up and ready to go."""
    console.print(f"\n[bold]noidea[/bold] v{__version__}\n")
    _check_repository()
    _check_hook()
    _config, llm = _check_config()
    _check_api_keys()
    console.print(f"Small Model:    {llm['small_model']}")
    console.print(f"Large Model:    {llm['large_model']}")
    console.print(f"Context Limit:  {llm['context_limit']}")
    console.print(f"Temperature:    {llm['temperature']}")
    console.print()
