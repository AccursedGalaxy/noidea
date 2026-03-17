import typer

from noidea.config import load_config
from noidea.git import get_diff, install_hook
from noidea.provider import get_commit_message

app = typer.Typer()


@app.command()
def init():
    install_hook()
    print("Git hook installed successfully.")


@app.command()
def suggest(file: str = typer.Option(None, "--file", "-F")):
    diff = get_diff()
    if diff == "none":
        print("No Changes have been detected")
    config = load_config()
    commit_message = get_commit_message(
        diff,
        config["llm"]["system_prompt"],
        config["llm"]["model"],
        config["llm"]["max_tokens"],
    )
    if file:
        with open(file, "w") as f:
            f.write(commit_message)
    else:
        print(commit_message)


if __name__ == "__main__":
    app()
