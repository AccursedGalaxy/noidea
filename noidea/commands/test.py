import random

import anthropic
from rich.console import Console

from noidea.config import load_config
from noidea.provider import get_commit_message

console = Console()

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
    config = load_config()
    llm = config["llm"]
    topic = random.choice(JOKE_TOPICS)

    try:
        with console.status("[grey]Checking systems...", spinner="dots"):
            test_msg = get_commit_message(
                diff=f"tell a creative short coding joke about {topic}",
                system_prompt="only output the joke nothing else. be original and avoid cliché jokes.",
                model=llm["large_model"],
                max_tokens=llm["max_tokens"],
                temperature=1.0,
            )
    # Same API error pattern as suggest.py, with messages suited to the test context.
    except KeyboardInterrupt:
        raise
    except anthropic.AuthenticationError as error:
        print(f"Authentication failed. Check your API key: {error.message}")
        return
    except anthropic.RateLimitError as error:
        print(f"Rate limited. Try again shortly: {error.message}")
        return
    except anthropic.APIConnectionError as error:
        print(f"Couldn't reach the API: {error}")
        return
    except anthropic.APIStatusError as error:
        print(f"API error ({error.status_code}): {error.message}")
        return

    print("The AI is alive and well.")
    print(f"It said: {test_msg}")
