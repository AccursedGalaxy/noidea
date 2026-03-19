from typing import Optional

import typer

from noidea import __version__
from noidea.commands import init, keys_app, status, suggest, test, update
from noidea.config import initialize

app = typer.Typer(
    name="noidea",
    rich_markup_mode="rich",
    no_args_is_help=True,
    help="AI-powered git commit messages.",
)
app.add_typer(keys_app, name="keys")

app.command()(init.init)
app.command()(status.status)
app.command()(suggest.suggest)
app.command()(test.test)
app.command()(update.update)


def version_callback(value: bool):
    if value:
        typer.echo(f"noidea {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    initialize()


if __name__ == "__main__":
    app()
