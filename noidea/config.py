"""Three-tier configuration: built-in defaults, user overrides, repo overrides."""

import dataclasses
import hashlib
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
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    OPENROUTER = "openrouter"


# The (small, large) model pair each provider starts with, so that setting only llm.provider works.
# Model names are provider-specific: a Claude ID sent to any other provider is a 404. Ollama has
# no entry that could be right in advance, because its models are whatever the user pulled; ""
# means "ask the local server" (see provider.resolve_models).
PROVIDER_DEFAULT_MODELS = {
    Provider.ANTHROPIC.value: ("claude-haiku-5-5", "claude-sonnet-5-5"),
    Provider.OPENAI.value: ("gpt-6-luna", "gpt-6.1-sol"),
    Provider.OLLAMA.value: ("", ""),
    Provider.GEMINI.value: ("gemini-3.8-flash", "gemini-4-argon"),
    Provider.DEEPSEEK.value: ("deepseek-flash", "deepseek-v4-pro"),
    # Groq's production models that do not reason: its reasoning models default to a 1024-token
    # completion budget, which reasoning alone can exhaust before the message is written.
    Provider.GROQ.value: ("llama-3.1-8b-instant", "llama-3.3-70b-versatile"),
    Provider.OPENROUTER.value: ("anthropic/claude-haiku-5.5", "anthropic/claude-sonnet-5.5"),
}
assert set(PROVIDER_DEFAULT_MODELS) == {member.value for member in Provider}


@dataclass(frozen=True)
class LlmConfig:
    """The LLM settings, owning the field set in one place: defaults are the field defaults.

    Built from a merged config dict via ``from_dict``, which coerces wrong-typed values
    back to their default (a corrupt user config warns rather than crashes). ``__post_init__``
    then asserts the type invariants that ``from_dict`` and the defaults both guarantee.
    """

    # Current Claude models think before they answer and spend part of this budget doing so.
    max_tokens: int = 8192
    small_model: str = PROVIDER_DEFAULT_MODELS[Provider.ANTHROPIC.value][0]
    large_model: str = PROVIDER_DEFAULT_MODELS[Provider.ANTHROPIC.value][1]
    # Characters (prompt plus diff) at which a change escalates to the large model: ~10k tokens,
    # well inside the small model's window, so the strong model sees big diffs uncut.
    context_limit: float = 40000.0
    # Hard ceiling on the diff characters sent to the model, applied below the selected model's own
    # context window (see suggest._diff_budget_chars). The default is a cost guard: with 1M-token
    # windows the window alone would let a hook send a vendored tree (hundreds of thousands of
    # tokens) on every commit attempt. 200k characters is ~65k tokens, far more than a commit
    # message needs. 0 means "auto": the window alone bounds the diff. Either way an enormous
    # staged change is truncated rather than allowed to overflow the window and fail; the full
    # changed-file list travels separately in the prompt, so every file is still named.
    diff_chars_max: int = 200_000
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    temperature: float = 1.0
    learn_commit_style: bool = True  # Match the repo's observed commit conventions.
    provider: str = "anthropic"  # Which backend complete() dispatches to; see provider.py.
    base_url: str = ""  # Overrides the per-provider default endpoint (e.g. a custom vLLM host).
    # The agent backend (driver-os): an alternative generator that explores the repo (git log,
    # style docs, the changed files) over several turns instead of one single-shot call. See
    # dogfood.py / agent_backend.py.
    # Default backend: when true, `noidea suggest` and the commit hook run the agent.
    use_agent: bool = False
    # Path to the driver-os commit-msg binary; "" falls back to NOIDEA_AGENT_BIN / PATH.
    agent_binary: str = ""
    agent_model: str = "google/gemini-3-flash-preview"  # OpenRouter model the agent runs on.
    # How long a queued agent proposal stays eligible to seed a commit.
    agent_proposal_ttl_seconds: int = 3600

    def __post_init__(self):
        # The pair to from_dict's pre-construction type check: assert the invariants
        # after construction, so a bad dataclasses.replace is caught as a programmer error.
        assert isinstance(self.max_tokens, int) and not isinstance(self.max_tokens, bool)
        assert isinstance(self.small_model, str)
        assert isinstance(self.large_model, str)
        assert isinstance(self.context_limit, (int, float))
        assert not isinstance(self.context_limit, bool)
        assert isinstance(self.diff_chars_max, int) and not isinstance(self.diff_chars_max, bool)
        assert self.diff_chars_max >= 0, "diff_chars_max must be non-negative (0 = auto)"
        assert isinstance(self.system_prompt, str)
        assert isinstance(self.temperature, (int, float))
        assert not isinstance(self.temperature, bool)
        assert isinstance(self.learn_commit_style, bool)
        assert isinstance(self.provider, str)
        assert isinstance(self.base_url, str)
        assert isinstance(self.use_agent, bool)
        assert isinstance(self.agent_binary, str)
        assert isinstance(self.agent_model, str)
        assert isinstance(self.agent_proposal_ttl_seconds, int) and not isinstance(
            self.agent_proposal_ttl_seconds, bool
        )

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
        # A type-valid but unknown provider (a hand-edited typo) is coerced back to the default
        # here, so it warns now rather than crashing later inside complete() with a raw ValueError.
        known_providers = {member.value for member in Provider}
        if values["provider"] not in known_providers:
            print(
                f"Warning: llm.provider {values['provider']!r} is not a known provider,"
                " using default.",
                file=sys.stderr,
            )
            values["provider"] = defaults.provider
        # A model nobody set comes from the provider's own pair: the field default is a Claude ID,
        # which every other provider rejects. A set model always wins, even one that equals a
        # Claude ID, since an OpenAI-compatible gateway can serve Claude under that name.
        small_default, large_default = PROVIDER_DEFAULT_MODELS[values["provider"]]
        if "small_model" not in data:
            values["small_model"] = small_default
        if "large_model" not in data:
            values["large_model"] = large_default
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


# Before 1.3.0, initialize() wrote every default into ~/.noidea/config.json, freezing them there:
# a later default change never reached an existing user. A user-config value equal to one of these
# old defaults is therefore treated as unset. System prompts are matched by SHA-256 because the
# old default texts are long.
_LEGACY_DEFAULTS = {
    "max_tokens": (1024,),
    "small_model": ("claude-haiku-4-5",),
    "large_model": ("claude-sonnet-4-6",),
    "context_limit": (600000, 600000.0),
}
_LEGACY_SYSTEM_PROMPT_SHA256 = frozenset(
    {
        "31aa6598c66b8d9b58f05451e189abd3c8847bf28bf7c0dfe04c4cb2063d7320",
        "32efdd2d9ab32a45823c56a5d1a9189307bc9b2a9fe7d9429376ba046722e681",
        "a74318533127e6718f0b28d5073612446f076ea1f2dd328e3f08e7e491f87c34",
        "bc54cdf365dab5901639d7e301ef5efe8833d7a650d280464a5da60fb85ff4a1",
        "bfcc5dbf03118c173c98d1fd0c3b8e8c56c7fefc7034b0abb9272d9379e8aaeb",
        "deb95abcd18cd86d3be49f24ec4274c5b9264ec1c834375e549ae55d57b8bfe3",
        "e3b1994174b3ee0d2bd99171d1b041990d2c9727030325504a2c36d54d5b9ba3",
        "e8ee51df4a303bfd64301791bd08cfffec874e96823cf888c9e5cb4e00194b35",
    }
)


def _drop_frozen_defaults(llm_section: dict) -> dict:
    """Remove values an older initialize() froze into the user config, so new defaults apply."""
    assert isinstance(llm_section, dict), "llm_section must be a dict"
    kept = {}
    for key, value in llm_section.items():
        if key in _LEGACY_DEFAULTS and value in _LEGACY_DEFAULTS[key]:
            continue
        if key == "system_prompt" and isinstance(value, str):
            if hashlib.sha256(value.encode()).hexdigest() in _LEGACY_SYSTEM_PROMPT_SHA256:
                continue
        kept[key] = value
    assert len(kept) <= len(llm_section), "dropping can only remove keys"
    return kept


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
    # Merge order: user config → repo config (last wins), then LlmConfig.from_dict fills every
    # absent field with its default. Defaults stay out of the merge so from_dict can tell a
    # setting nobody made from one that happens to equal a default (see the provider model pair).
    config: dict = {"llm": {}}
    for path in _collect_config_paths():
        try:
            with open(path) as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            # Warn instead of crashing: a corrupt config should not block all CLI usage.
            print(f"Warning: could not load {path}: {error}", file=sys.stderr)
            continue
        # Only the user file was ever written by initialize(); a repo config is deliberate.
        if path == CONFIG_PATH and isinstance(loaded, dict) and isinstance(loaded.get("llm"), dict):
            loaded = {**loaded, "llm": _drop_frozen_defaults(loaded["llm"])}
        config = deep_merge(config, loaded)
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
            # An empty section, not the defaults: written values would freeze today's defaults
            # for this user. Every setting is documented in docs/configuration.md.
            with open(CONFIG_PATH, "w") as f:
                json.dump({"llm": {}}, f, indent=2)
        except OSError as error:
            print(f"Warning: could not write {CONFIG_PATH}: {error}", file=sys.stderr)

    # The API-key registry is owned by key_store, which creates keys.json lazily on first add.
