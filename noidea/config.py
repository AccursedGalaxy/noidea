"""Three-tier configuration: built-in defaults, user overrides, repo overrides."""

import dataclasses
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum

from noidea.git import get_git_root

SERVICE_NAME = "noidea"
CONFIG_DIR_NAME = ".noidea"
CONFIG_FILENAME = "config.json"

CONFIG_DIR = os.path.expanduser(f"~/{CONFIG_DIR_NAME}")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILENAME)

_DEFAULT_SYSTEM_PROMPT = (
    "Generate a commit message from the diff, branch name, and staged files.\n"
    "Subject: imperative mood, max 72 chars, no period, "
    "conventional commits format (e.g. feat(scope): ..., fix(scope): ...).\n"
    "One intent per subject — no 'and'. Use branch name to infer purpose.\n"
    "Prefer specific verbs over generic ones (update, add, remove).\n"
    "Body: only if the why or scope is non-obvious. "
    "Use bullet points for multi-change commits, "
    "one action per bullet. Keep each line under 72 chars. No fluff.\n"
    "Output only the raw commit message."
)


class Provider(str, Enum):
    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class LlmConfig:
    """The LLM settings, owning the field set in one place: defaults are the field defaults.

    Built from a merged config dict via ``from_dict``, which coerces wrong-typed values
    back to their default (a corrupt user config warns rather than crashes). ``__post_init__``
    then asserts the type invariants that ``from_dict`` and the defaults both guarantee.
    """

    max_tokens: int = 1024
    small_model: str = "claude-haiku-4-5"
    large_model: str = "claude-sonnet-4-6"
    context_limit: float = 600000.0  # Character threshold for model selection, not a token limit.
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    temperature: float = 1.0
    learn_commit_style: bool = True  # Match the repo's observed commit conventions.

    def __post_init__(self):
        # The pair to from_dict's pre-construction type check: assert the invariants
        # after construction, so a bad dataclasses.replace is caught as a programmer error.
        assert isinstance(self.max_tokens, int) and not isinstance(self.max_tokens, bool)
        assert isinstance(self.small_model, str)
        assert isinstance(self.large_model, str)
        assert isinstance(self.context_limit, (int, float))
        assert not isinstance(self.context_limit, bool)
        assert isinstance(self.system_prompt, str)
        assert isinstance(self.temperature, (int, float))
        assert not isinstance(self.temperature, bool)
        assert isinstance(self.learn_commit_style, bool)

    @classmethod
    def from_dict(cls, data: dict) -> "LlmConfig":
        """Build from a merged ``llm`` dict, falling back to the default for any bad field.

        A field is "bad" when it is absent or has the wrong type; bool is never accepted for
        a numeric field even though it is an ``int`` subclass. Each fallback warns to stderr.
        """
        assert isinstance(data, dict), "data must be a dict"
        defaults = cls()
        values = {}
        for spec in dataclasses.fields(cls):
            default = getattr(defaults, spec.name)
            provided = data.get(spec.name, default)
            if _matches_default_type(provided, default):
                values[spec.name] = provided
            else:
                print(
                    f"Warning: llm.{spec.name} has wrong type"
                    f" ({type(provided).__name__}), using default.",
                    file=sys.stderr,
                )
                values[spec.name] = default
        result = cls(**values)
        assert isinstance(result, LlmConfig), "from_dict must return an LlmConfig"
        return result

    def select_model(self, context_length_chars: int) -> str:
        """Pick the large or small model based on a character-count heuristic."""
        assert isinstance(context_length_chars, int), "context_length_chars must be an int"
        assert context_length_chars >= 0, "context_length_chars must be non-negative"
        if context_length_chars >= self.context_limit:
            return self.large_model
        return self.small_model


def _matches_default_type(value, default) -> bool:
    """True if ``value`` is type-compatible with ``default`` (numeric defaults accept int/float)."""
    # A bool default (e.g. learn_commit_style) accepts only a bool.
    if isinstance(default, bool):
        return isinstance(value, bool)
    # bool is an int subclass but is never a valid value for a numeric/str field, so reject it.
    if isinstance(value, bool):
        return False
    if isinstance(default, float):
        return isinstance(value, (int, float))
    return isinstance(value, type(default))


# Derived from the dataclass so the field set is enumerated exactly once. Used as the merge
# base and written verbatim by initialize().
DEFAULTS = {"llm": dataclasses.asdict(LlmConfig())}


def deep_merge(base, override):
    # Iterative stack-based merge to guarantee bounded execution depth.
    result = base.copy()
    stack = [(result, override)]

    while stack:
        target, source = stack.pop()
        for key, value in source.items():
            if key in target and isinstance(value, dict) and isinstance(target[key], dict):
                target[key] = target[key].copy()
                stack.append((target[key], value))
            else:
                target[key] = value

    return result


def _collect_config_paths() -> list[str]:
    """Gather user and repo config file paths that exist on disk."""
    paths = []
    if os.path.exists(CONFIG_PATH):
        paths.append(CONFIG_PATH)
    repo_root = get_git_root()
    if repo_root:
        repo_path = os.path.join(repo_root, CONFIG_DIR_NAME, CONFIG_FILENAME)
        if os.path.exists(repo_path):
            paths.append(repo_path)
    return paths


def load_config() -> LlmConfig:
    # Merge order: defaults → user config → repo config (last wins). The merge stays
    # dict-shaped (deep_merge handles arbitrary nested JSON); the typed LlmConfig is
    # constructed last, from the merged dict.
    config = DEFAULTS
    for path in _collect_config_paths():
        try:
            with open(path) as f:
                config = deep_merge(config, json.load(f))
        except (OSError, json.JSONDecodeError) as error:
            # Warn instead of crashing: a corrupt config should not block all CLI usage.
            print(f"Warning: could not load {path}: {error}", file=sys.stderr)
    llm_section = config.get("llm")
    if not isinstance(llm_section, dict):
        # A non-dict llm section is corrupt; fall back to an all-default config.
        print(
            "Warning: config 'llm' section is not a dict, using defaults.",
            file=sys.stderr,
        )
        llm_section = {}
    cfg = LlmConfig.from_dict(llm_section)
    assert isinstance(cfg, LlmConfig), "load_config must return an LlmConfig"
    return cfg


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

    # The API-key registry is owned by key_store, which creates keys.json lazily on first add.
