import os

import keyring
from rich.console import Console

from noidea import __version__
from noidea.config import config_path, list_keys, load_config
from noidea.git import get_git_root, get_hooks_dir

console = Console(stderr=True)

OK = "[green]\u2713[/green]"
FAIL = "[red]\u2717[/red]"


def status():
    """Show current noidea configuration, API keys, and hook status."""
    console.print(f"\n[bold]noidea[/bold] v{__version__}\n")

    # Repository
    repo_root = get_git_root()
    if repo_root:
        console.print(f"Repository:     {OK} git repo detected")
    else:
        console.print(f"Repository:     {FAIL} not a git repository")

    # Hook
    hooks_dir = get_hooks_dir()
    if hooks_dir:
        hook_path = os.path.join(hooks_dir, "prepare-commit-msg")
        if os.path.exists(hook_path):
            with open(hook_path) as f:
                content = f.read()
            if "noidea" in content:
                console.print(
                    f"Hook:           {OK} prepare-commit-msg installed ({hooks_dir})"
                )
            else:
                console.print(
                    f"Hook:           [yellow]![/yellow] prepare-commit-msg exists but not managed by noidea"
                )
        else:
            console.print(f"Hook:           {FAIL} prepare-commit-msg not found")
    else:
        console.print(f"Hook:           {FAIL} prepare-commit-msg not found")

    # Config
    config = load_config()
    llm = config["llm"]
    if os.path.exists(config_path):
        console.print(f"Config:         {OK} {config_path} loaded")
    else:
        console.print(f"Config:         [dim]using defaults[/dim]")

    # API key
    try:
        keys = list_keys()
        if keys:
            for key in keys:
                stored = keyring.get_password("noidea", key)
                if stored:
                    console.print(f"API Key:        {OK} {key} (keyring)")
                else:
                    console.print(
                        f"API Key:        {FAIL} {key} registered but missing from keyring"
                    )
        else:
            console.print(
                f"API Key:        {FAIL} no key found (run 'noidea keys add')"
            )
    except Exception:
        console.print(f"API Key:        {FAIL} could not read keys")

    # Model config
    console.print(f"Small Model:    {llm['small_model']}")
    console.print(f"Large Model:    {llm['large_model']}")
    console.print(f"Context Limit:  {llm['context_limit']}")
    console.print()
