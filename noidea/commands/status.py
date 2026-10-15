import os

from rich.console import Console

from noidea import build_version
from noidea.config import CONFIG_PATH, SERVICE_NAME, LlmConfig, load_config
from noidea.git import HOOKS, get_git_root, get_hooks_dir, is_noidea_hook
from noidea.key_store import KeyStatus, KeyStoreError, env_var_for, key_store

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
        console.print(f"Hook:           {FAIL} not in a git repository")
        return
    # Report every managed hook: prepare-commit-msg writes the message, post-commit captures
    # the accept/edit/discard signal. A half-installed pair is worth surfacing here.
    for name in HOOKS:
        _report_one_hook(hooks_dir, name)


def _report_one_hook(hooks_dir: str, name: str) -> None:
    """Report the install state of a single managed hook by name."""
    assert isinstance(name, str) and name, "hook name must be non-empty"
    hook_path = os.path.join(hooks_dir, name)
    if not os.path.exists(hook_path):
        console.print(f"Hook:           {FAIL} {name} not found")
        return
    try:
        with open(hook_path) as f:
            content = f.read()
    except OSError:
        console.print(f"Hook:           {FAIL} could not read {name}")
        return
    # A package upgrade never rewrites hooks already in a repo, so an older noidea script keeps
    # running stale behaviour until `noidea init` replaces it. Say so rather than report it OK.
    if content == HOOKS[name]:
        console.print(f"Hook:           {OK} {name} installed ({hooks_dir})")
    elif is_noidea_hook(content):
        console.print(
            f"Hook:           [yellow]![/yellow] {name} outdated"
            f" (run '{SERVICE_NAME} init' to update)"
        )
    else:
        console.print(
            f"Hook:           [yellow]![/yellow] {name} exists"
            f" but not managed by {SERVICE_NAME}"
        )


def _check_config() -> LlmConfig:
    cfg = load_config()
    if os.path.exists(CONFIG_PATH):
        console.print(f"Config:         {OK} {CONFIG_PATH} loaded")
    else:
        console.print("Config:         [dim]using defaults[/dim]")
    return cfg


def _check_api_key(cfg: LlmConfig) -> None:
    """Report the key the configured provider needs, and where it comes from."""
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    provider = cfg.provider
    env_var = env_var_for(provider)
    # Only keyless providers (ollama) have no env var; see key_store._PROVIDER_ENV_VARS.
    if env_var is None:
        console.print(f"API Key:        {OK} not needed ({provider})")
        return
    try:
        key_status = key_store.status_of(provider)
    except KeyStoreError:
        console.print(f"API Key:        {FAIL} could not read the keyring")
        return
    if key_status is KeyStatus.PRESENT:
        console.print(f"API Key:        {OK} {provider} (keyring)")
    elif os.environ.get(env_var):
        console.print(f"API Key:        {OK} {provider} ({env_var})")
    elif key_status is KeyStatus.MISSING_SECRET:
        console.print(
            f"API Key:        {FAIL} {provider} registered but missing from keyring"
            f" (run '{SERVICE_NAME} keys add {provider}')"
        )
    else:
        console.print(
            f"API Key:        {FAIL} no key for {provider}"
            f" (run '{SERVICE_NAME} keys add {provider}' or set {env_var})"
        )


def status():
    """Check if everything's wired up and ready to go."""
    console.print(f"\n[bold]noidea[/bold] v{build_version()}\n")
    _check_repository()
    _check_hook()
    cfg = _check_config()
    console.print(f"Provider:       {cfg.provider}")
    _check_api_key(cfg)
    console.print(f"Small Model:    {cfg.small_model}")
    console.print(f"Large Model:    {cfg.large_model}")
    console.print(f"Context Limit:  {cfg.context_limit:g} characters")
    console.print(f"Temperature:    {cfg.temperature}")
    console.print()
