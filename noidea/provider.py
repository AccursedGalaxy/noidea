import os

from anthropic import Anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


def get_commit_message(
    diff: str, system_prompt: str, model: str, max_tokens: int
) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        system=system_prompt,
        messages=[{"role": "user", "content": diff}],
        max_tokens=1024,
    )
    block = message.content[0]
    assert isinstance(block, TextBlock)
    return block.text
