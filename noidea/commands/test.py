from noidea.config import load_config
from noidea.provider import get_commit_message


def test():
    """Send a dummy message to the API to test."""
    try:
        config = load_config()
        llm = config["llm"]
        test_msg = get_commit_message(
            diff="say hi",
            system_prompt="test",
            model=llm["large_model"],
            max_tokens=llm["max_tokens"],
        )
        print("Test successful!")
        print(f"API response: {test_msg}")
    except Exception as e:
        print(f"Something went wrong: {e}")
