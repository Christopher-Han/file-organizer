from pathlib import Path

from typer.testing import CliRunner

from organizer.cli.main import app
from organizer.config import load_organizer_paths

runner = CliRunner()


def test_memory_cli_show_and_set(tmp_path: Path) -> None:
    base_dir = tmp_path / "state"
    result = runner.invoke(app, ["memory", "set-pref", "tone", "casual", "--base-dir", str(base_dir)])
    assert result.exit_code == 0, result.output

    show = runner.invoke(app, ["memory", "show", "--base-dir", str(base_dir)])
    assert show.exit_code == 0, show.output
    paths = load_organizer_paths(base_dir=base_dir)
    stored = paths.memory_file.read_text(encoding="utf-8")
    assert "casual" in stored
