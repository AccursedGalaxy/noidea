import random

from rich.console import Console

from noidea.config import load_config
from noidea.provider import ErrorKind, ProviderError, complete

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

# Wording per failure kind, suited to the test context; keyed on ErrorKind so a new kind
# forces a deliberate update. The connection message differs from suggest's on purpose.
TEST_WORDING = {
    ErrorKind.AUTH: lambda e: f"Authentication failed. Check your API key: {e.message}",
    ErrorKind.RATE_LIMIT: lambda e: f"Rate limited. Try again shortly: {e.message}",
    ErrorKind.CONNECTION: lambda e: f"Couldn't reach the API: {e.message}",
    ErrorKind.STATUS: lambda e: f"API error ({e.status_code}): {e.message}",
}
assert set(TEST_WORDING) == set(ErrorKind), "TEST_WORDING must cover every ErrorKind"


def test():
    """Ping the AI to make sure it's awake."""
    cfg = load_config()
    topic = random.choice(JOKE_TOPICS)

    # test calls complete() directly: it wants a generic completion, not a commit message.
    try:
        with console.status("[grey]Checking systems...", spinner="dots"):
            joke = complete(
                "only output the joke nothing else. be original and avoid cliché jokes.",
                f"tell a creative short coding joke about {topic}",
                cfg.large_model,
                cfg.max_tokens,
            )
    except ProviderError as error:
        print(TEST_WORDING[error.kind](error))
        return

    print("The AI is alive and well.")
    print(f"It said: {joke}")
