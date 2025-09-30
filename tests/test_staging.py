"""Tests for staging, applying, and rolling back manifests."""

from __future__ import annotations

from pathlib import Path

import pytest

from organizer.config import load_organizer_paths
from organizer.models import SuggestedChange
from organizer.staging import (
    apply_manifest,
    load_manifest,
    preview_diff,
    rollback_manifest,
    stage_changes,
)


@pytest.fixture()
def project_paths(tmp_path: Path):
    workdir = tmp_path / "work"
    return load_organizer_paths(base_dir=workdir)


def _write_file(path: Path, content: str = "sample") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_stage_apply_and_rollback_move(project_paths):
    source = project_paths.root / "downloads" / "file.txt"
    destination = project_paths.root / "archive" / "file.txt"
    _write_file(source, "data")

    change = SuggestedChange(
        rule_name="Move",
        source=source,
        destination=destination,
        action_type="move",
    )

    manifest = stage_changes([change], project_paths, manifest_id="test1")
    assert manifest.identifier == "test1"
    assert "MOVE" in preview_diff(manifest)

    loaded_manifest = load_manifest(project_paths, manifest.identifier)
    log_manifest_path = apply_manifest(project_paths, loaded_manifest)
    assert destination.exists()
    assert not source.exists()
    assert log_manifest_path.exists()

    rollback_manifest(project_paths, loaded_manifest.identifier)
    assert source.exists()
    assert not destination.exists()


def test_apply_missing_staged_file_raises(project_paths):
    source = project_paths.root / "downloads" / "doc.txt"
    destination = project_paths.root / "archive" / "doc.txt"
    _write_file(source, "hello")

    change = SuggestedChange(
        rule_name="Move",
        source=source,
        destination=destination,
        action_type="move",
    )

    manifest = stage_changes([change], project_paths, manifest_id="test2")
    staged_file = manifest.path.parent / manifest.entries[0].staged_relpath
    staged_file.unlink()

    with pytest.raises(FileNotFoundError):
        apply_manifest(project_paths, manifest)

