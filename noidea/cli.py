"""Typer application entry point: registers commands and runs global setup."""

from typing import Optional

import typer

from noidea import build_version
from noidea.commands import init, keys_app, reconcile, status, suggest, test, update
from noidea.config import initialize

app = typer.Typer(
    name="noidea",
    rich_markup_mode="rich",
    no_args_is_help=True,
    help="You have no idea what to write in your commits? We got you.",
)
app.add_typer(keys_app, name="keys")

app.command()(init.init)
app.command()(status.status)
app.command()(suggest.suggest)
app.command()(test.test)
app.command()(update.update)
# Hidden: the post-commit hook calls this to capture the accept/edit/discard signal. It is
# plumbing, not a user-facing command, so it stays out of --help.
app.command(name="_reconcile", hidden=True)(reconcile.reconcile)


def version_callback(value: bool):
    if value:
        typer.echo(f"noidea {build_version()} — no idea required")
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
