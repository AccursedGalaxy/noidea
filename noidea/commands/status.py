import os

from rich.console import Console

from noidea import __version__
from noidea.config import CONFIG_PATH, SERVICE_NAME, LlmConfig, load_config
from noidea.git import HOOK_NAME, get_git_root, get_hooks_dir
from noidea.key_store import KeyStatus, KeyStoreError, key_store

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


def _check_config() -> LlmConfig:
    cfg = load_config()
    if os.path.exists(CONFIG_PATH):
        console.print(f"Config:         {OK} {CONFIG_PATH} loaded")
    else:
        console.print("Config:         [dim]using defaults[/dim]")
    return cfg


def _check_api_keys():
    try:
        keys = key_store.list()
        if not keys:
            console.print(f"API Key:        {FAIL} no key found (run 'noidea keys add')")
            return
        for key in keys:
            if key_store.status_of(key) is KeyStatus.PRESENT:
                console.print(f"API Key:        {OK} {key} (keyring)")
            else:
                console.print(f"API Key:        {FAIL} {key} registered but missing from keyring")
    except KeyStoreError:
        console.print(f"API Key:        {FAIL} could not read keys")


def status():
    """Check if everything's wired up and ready to go."""
    console.print(f"\n[bold]noidea[/bold] v{__version__}\n")
    _check_repository()
    _check_hook()
    cfg = _check_config()
    _check_api_keys()
    console.print(f"Small Model:    {cfg.small_model}")
    console.print(f"Large Model:    {cfg.large_model}")
    console.print(f"Context Limit:  {cfg.context_limit}")
    console.print(f"Temperature:    {cfg.temperature}")
    console.print()
