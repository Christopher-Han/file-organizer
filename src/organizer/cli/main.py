"""Command-line entry point for the Agentic File Organizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from organizer.config import load_organizer_paths
from organizer.llm import LlamaClient
from organizer.storage import JsonMemoryStore

app = typer.Typer(help="Interact with the Agentic File Organizer tooling.")
memory_app = typer.Typer(help="Inspect and update organizer memory.")
app.add_typer(memory_app, name="memory")


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


@app.command("configure-llm")
def configure_llm(
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        prompt="Enter your Llama API key",
        hide_input=True,
        help="API key issued for the hosted Llama API.",
    ),
    base_dir: Optional[Path] = typer.Option(
        None,
        "--base-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        resolve_path=True,
        help="Store the key using an alternate base directory.",
    ),
) -> None:
    """Persist the Llama API key used for agent completions."""

    if api_key is None:
        raise typer.BadParameter("API key entry cancelled")

    paths = load_organizer_paths(base_dir=base_dir)
    client = LlamaClient(paths)
    client.set_api_key(api_key)
    typer.echo("Llama API key stored for future sessions.")


@memory_app.command("show")
def memory_show(
    base_dir: Optional[Path] = typer.Option(
        None,
        "--base-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        resolve_path=True,
        help="Read memory data from an alternate base directory.",
    ),
) -> None:
    """Print the stored organizer memory payload."""

    paths = load_organizer_paths(base_dir=base_dir)
    store = JsonMemoryStore(paths.memory_file, default_payload={"rules": [], "preferences": {}})
    memory = store.load()
    typer.echo(typer.style("Current organizer memory:", bold=True))
    typer.echo(json.dumps(memory, indent=2))


@memory_app.command("set-pref")
def memory_set_preference(
    key: str = typer.Argument(..., help="Preference key to update."),
    value: str = typer.Argument(..., help="New value; parsed as JSON when possible."),
    base_dir: Optional[Path] = typer.Option(
        None,
        "--base-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        resolve_path=True,
        help="Persist changes in an alternate base directory.",
    ),
) -> None:
    """Update a preference value stored in memory."""

    paths = load_organizer_paths(base_dir=base_dir)
    store = JsonMemoryStore(paths.memory_file, default_payload={"rules": [], "preferences": {}})
    memory = store.load()
    preferences = memory.setdefault("preferences", {})
    preferences[key] = _coerce_value(value)
    store.save(memory)
    typer.echo(f"Preference '{key}' updated.")


def _coerce_value(raw: str) -> Any:
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered.isdigit():
        return int(lowered)
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        return json.loads(raw)
    except Exception:  # pragma: no cover - fallback to raw string
        return raw


if __name__ == "__main__":  # pragma: no cover
    app()
