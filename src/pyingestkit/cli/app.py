from __future__ import annotations

from typing import Annotated

import typer

from pyingestkit import __version__
from pyingestkit.cli.commands import inspect_command, jobs_command, run_command, runs_command, status_command
from pyingestkit.cli.console import console


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pyingest {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="pyingest",
    help="Build and run reliable ingestion jobs with PyIngestKit.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
    suggest_commands=True,
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show the PyIngestKit CLI version and exit.", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    del version


app.command("jobs", help="List installed ingestion jobs.")(jobs_command)
app.command("inspect", help="Inspect an installed ingestion job.")(inspect_command)
app.command("run", help="Execute an installed ingestion job.")(run_command)
app.command("runs", help="List persisted ingestion runs.")(runs_command)
app.command("status", help="Inspect one persisted ingestion run.")(status_command)


@app.command("help")
def help_command(ctx: typer.Context) -> None:
    """Show the main CLI help. Use `COMMAND --help` for command-specific help."""
    parent = ctx.parent
    console.print(parent.get_help() if parent is not None else ctx.get_help())
