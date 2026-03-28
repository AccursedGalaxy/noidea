"""Thin Anthropic API wrapper: key retrieval and commit message generation."""

import os

import keyring
from anthropic import Anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv

from noidea.config import SERVICE_NAME, Provider

load_dotenv()


def get_api_key(provider: Provider = Provider.ANTHROPIC) -> str:
    # Keyring first: credentials stay out of the process environment.
    key = keyring.get_password(service_name=SERVICE_NAME, username=provider.value)
    if not key:
        # Fall back to env var for CI and headless environments.
        key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("No API key found. Run 'noidea keys add'.")
    return key


def get_commit_message(
    diff: str,
    system_prompt: str,
    model: str,
    max_tokens: int,
    branch: str = "",
    staged_files: list[str] | None = None,
    temperature: float = 1.0,
) -> str:
    # Validate inputs at the API boundary before spending a network round-trip.
    if not isinstance(diff, str) or not diff.strip():
        raise ValueError("diff must be a non-empty string")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt must be a non-empty string")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise TypeError(f"max_tokens must be a positive integer, got {type(max_tokens).__name__}")
    if not isinstance(temperature, (int, float)) or temperature < 0:
        raise TypeError(f"temperature must be a non-negative number, got {temperature!r}")

    context_parts = []
    if branch:
        context_parts.append(f"Branch: {branch}")
    if staged_files:
        context_parts.append("Staged files:\n" + "\n".join(f"- {f}" for f in staged_files))

    user_content = ""
    if context_parts:
        user_content = "\n".join(context_parts) + "\n\nDiff:\n"
    user_content += diff

    client = Anthropic(api_key=get_api_key())
    message = client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    block = message.content[0]
    # Claude can return tool_use or image blocks; we only handle text for commit messages.
    if not isinstance(block, TextBlock):
        raise TypeError(f"Expected TextBlock, got {type(block).__name__}")
    return block.text
