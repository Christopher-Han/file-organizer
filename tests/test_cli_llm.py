from pathlib import Path

from typer.testing import CliRunner

from organizer.cli.main import app
from organizer.config import load_organizer_paths


def test_configure_llm_stores_key(tmp_path: Path) -> None:
    runner = CliRunner()
    base_dir = tmp_path / "cfg"

    result = runner.invoke(
        app,
        ["configure-llm", "--api-key", "token-123", "--base-dir", str(base_dir)],
    )

    assert result.exit_code == 0, result.output
    paths = load_organizer_paths(base_dir=base_dir)
    assert paths.llama_api_key_file.read_text(encoding="utf-8") == "token-123"
