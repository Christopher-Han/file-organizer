from hashlib import sha256
from pathlib import Path

import pytest

from organizer.indexing import scan_paths


def test_scan_paths_filters_hidden_and_depth(tmp_path: Path) -> None:
    base = tmp_path / "workspace"
    nested = base / "nested"
    nested.mkdir(parents=True)

    root_file = base / "root.txt"
    root_file.write_text("root")
    nested_file = nested / "nested.txt"
    nested_file.write_text("nested")

    hidden_file = base / ".secret.txt"
    hidden_file.write_text("hidden")
    hidden_dir = base / ".shadow"
    hidden_dir.mkdir()
    hidden_dir_file = hidden_dir / "ghost.txt"
    hidden_dir_file.write_text("ghost")

    records, errors = scan_paths([base])
    assert errors == []
    assert {record.path.name for record in records} == {"root.txt", "nested.txt"}

    depth_limited, _ = scan_paths([base], max_depth=0)
    assert {record.path.name for record in depth_limited} == {"root.txt"}

    with_hidden, _ = scan_paths([base], include_hidden=True)
    assert {record.path.name for record in with_hidden} == {
        "root.txt",
        "nested.txt",
        ".secret.txt",
        "ghost.txt",
    }


def test_scan_single_file_with_checksum(tmp_path: Path) -> None:
    file_path = tmp_path / "note.txt"
    file_path.write_text("payload")

    records, errors = scan_paths([file_path], compute_checksums=True)
    assert errors == []
    assert len(records) == 1
    checksum = sha256(b"payload").hexdigest()
    assert records[0].checksum == checksum


def test_scan_reports_missing_paths(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    records, errors = scan_paths([missing])
    assert records == []
    assert errors and errors[0].message == "Path does not exist"

    with pytest.raises(ValueError):
        scan_paths([tmp_path], max_depth=-1)
