import os

import keyring
from anthropic import Anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv

load_dotenv()


def get_api_key() -> str:
    key = keyring.get_password(service_name="noidea", username="Anthropic")
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("No API key found. Run 'noidea keys add'.")
    return key


def get_commit_message(
    diff: str, system_prompt: str, model: str, max_tokens: int
) -> str:
    client = Anthropic(api_key=get_api_key())
    message = client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": diff}],
        max_tokens=max_tokens,
    )
    block = message.content[0]
    assert isinstance(block, TextBlock)
    return block.text
