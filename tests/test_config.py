from pathlib import Path

from organizer.config import load_organizer_paths


def test_load_organizer_paths_creates_directories(tmp_path: Path) -> None:
    base_dir = tmp_path / "organizer"
    assert not base_dir.exists()

    paths = load_organizer_paths(base_dir=base_dir)

    assert paths.root == base_dir.resolve()
    assert paths.memory_file == paths.root / "organizer.memory.json"
    assert paths.index_file == paths.root / "organizer.index.sqlite"
    assert paths.staging_dir == paths.root / "staging"
    assert paths.log_dir == paths.root / "logs"

    # Directories should be created on load.
    assert paths.root.is_dir()
    assert paths.staging_dir.is_dir()
    assert paths.log_dir.is_dir()
