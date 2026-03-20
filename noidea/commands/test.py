import random

from rich.console import Console

console = Console()

from noidea.config import load_config
from noidea.provider import get_commit_message

JOKE_TOPICS = [
    "recursion",
    "off-by-one errors",
    "git merge conflicts",
    "stack overflow",
    "null pointers",
    "regex",
    "CSS centering",
    "dependency hell",
    "legacy code",
    "code reviews",
    "documentation",
    "naming variables",
    "deadlocks",
    "segfaults",
    "production bugs",
]


def test():
    """Ping the AI to make sure it's awake."""
    try:
        config = load_config()
        llm = config["llm"]
        topic = random.choice(JOKE_TOPICS)
        with console.status("[grey]Checkig systems...", spinner="dots"):
            test_msg = get_commit_message(
                diff=f"tell a creative short coding joke about {topic}",
                system_prompt="only output the joke nothing else. be original and avoid cliché jokes.",
                model=llm["large_model"],
                max_tokens=llm["max_tokens"],
                temperature=1.0,
            )
        print("The AI is alive and well.")
        print(f"It said: {test_msg}")
    except Exception as e:
        print(f"Couldn't reach the API: {e}")
