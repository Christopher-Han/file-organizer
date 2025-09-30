"""Command-line entry point for the Agentic File Organizer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from organizer.config import load_organizer_paths

app = typer.Typer(help="Interact with the Agentic File Organizer tooling.")


@app.command()
def init(
    base_dir: Optional[Path] = typer.Option(
        None,
        "--base-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        resolve_path=True,
        help="Initialize the organizer using an alternate base directory.",
    ),
) -> None:
    """Ensure required directories exist and display their locations."""

    paths = load_organizer_paths(base_dir=base_dir)
    typer.echo("Organizer directories ready:")
    typer.echo(f"  root: {paths.root}")
    typer.echo(f"  memory: {paths.memory_file}")
    typer.echo(f"  index: {paths.index_file}")
    typer.echo(f"  staging: {paths.staging_dir}")
    typer.echo(f"  logs: {paths.log_dir}")


if __name__ == "__main__":  # pragma: no cover
    app()
