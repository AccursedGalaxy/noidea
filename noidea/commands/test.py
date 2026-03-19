from noidea.config import load_config
from noidea.provider import get_commit_message


def test():
    """Ping the AI to make sure it's awake."""
    try:
        config = load_config()
        llm = config["llm"]
        test_msg = get_commit_message(
            diff="tell a one line coding joke",
            system_prompt="",
            model=llm["large_model"],
            max_tokens=llm["max_tokens"],
        )
        print("The AI is alive and well.")
        print(f"It said: {test_msg}")
    except Exception as e:
        print(f"Couldn't reach the API: {e}")
