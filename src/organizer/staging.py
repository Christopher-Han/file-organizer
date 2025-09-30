"""Staging and manifest management for safe file operations."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Sequence

from .config import OrganizerPaths
from .models import SuggestedChange


@dataclass(frozen=True)
class StageEntry:
    """Metadata about a single staged change."""

    source_path: Path
    destination_path: Path
    action: str
    staged_relpath: str
    checksum: str


@dataclass(frozen=True)
class StageManifest:
    """Information about the manifest created during staging."""

    identifier: str
    path: Path
    entries: Sequence[StageEntry]


def stage_changes(
    changes: Sequence[SuggestedChange],
    paths: OrganizerPaths,
    *,
    manifest_id: str | None = None,
) -> StageManifest:
    """Copy files into the staging area and record a manifest."""

    if not changes:
        raise ValueError("No changes provided for staging")

    manifest_identifier = manifest_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    manifest_dir = paths.staging_dir / manifest_identifier
    manifest_dir.mkdir(parents=True, exist_ok=True)

    entries: list[StageEntry] = []
    for index, change in enumerate(changes):
        source_path = change.source.expanduser().resolve()
        destination_path = change.destination.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Source file missing during staging: {source_path}")

        staged_name = f"{index:04d}_{source_path.name}"
        staged_path = manifest_dir / staged_name
        shutil.copy2(source_path, staged_path)

        checksum = _sha256_file(staged_path)

        entries.append(
            StageEntry(
                source_path=source_path,
                destination_path=destination_path,
                action=change.action_type,
                staged_relpath=staged_name,
                checksum=checksum,
            )
        )

    manifest_path = manifest_dir / "manifest.json"
    _write_manifest(manifest_path, manifest_identifier, entries)

    return StageManifest(identifier=manifest_identifier, path=manifest_path, entries=tuple(entries))


def _write_manifest(manifest_path: Path, identifier: str, entries: Sequence[StageEntry]) -> None:
    manifest_data = {
        "id": identifier,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entries": [
            {
                "source_path": str(entry.source_path),
                "destination_path": str(entry.destination_path),
                "action": entry.action,
                "staged_relpath": entry.staged_relpath,
                "checksum": entry.checksum,
            }
            for entry in entries
        ],
    }

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest_data, handle, indent=2)


def load_manifest(paths: OrganizerPaths, manifest_id: str) -> StageManifest:
    """Load a manifest from disk."""

    manifest_dir = paths.staging_dir / manifest_id
    manifest_path = manifest_dir / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    entries = [
        StageEntry(
            source_path=Path(entry["source_path"]),
            destination_path=Path(entry["destination_path"]),
            action=entry["action"],
            staged_relpath=entry["staged_relpath"],
            checksum=entry["checksum"],
        )
        for entry in data["entries"]
    ]

    return StageManifest(identifier=data["id"], path=manifest_path, entries=tuple(entries))


def preview_diff(manifest: StageManifest) -> str:
    """Return a human-readable summary of a manifest."""

    lines = [f"Manifest {manifest.identifier} contains {len(manifest.entries)} change(s):"]
    for entry in manifest.entries:
        if entry.action == "tag":
            summary = f"TAG {entry.source_path}"
        elif entry.action == "trash":
            summary = f"TRASH {entry.source_path}"
        else:
            summary = f"{entry.action.upper()} {entry.source_path} -> {entry.destination_path}"
        lines.append(summary)
    return "\n".join(lines)


def apply_manifest(paths: OrganizerPaths, manifest: StageManifest) -> Path:
    """Apply a manifest's staged changes to the filesystem."""

    log_dir = (paths.log_dir / manifest.identifier).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_entries: list[dict[str, str | None]] = []

    for index, entry in enumerate(manifest.entries):
        if entry.action not in {"move", "rename"}:
            continue  # Non-filesystem actions require no mutation yet

        staged_path = manifest.path.parent / entry.staged_relpath
        if not staged_path.exists():
            raise FileNotFoundError(f"Missing staged file: {staged_path}")

        source_path = entry.source_path
        destination_path = entry.destination_path
        backup_source = log_dir / f"{index:04d}_source"
        backup_destination = None

        if destination_path.exists() and destination_path != source_path:
            backup_destination = log_dir / f"{index:04d}_dest"
            backup_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(destination_path, backup_destination)

        if source_path.exists():
            backup_source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(source_path, backup_source)
        else:
            raise FileNotFoundError(f"Source disappeared before apply: {source_path}")

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(staged_path, destination_path)

        log_entries.append(
            {
                "action": entry.action,
                "source_path": str(source_path),
                "destination_path": str(destination_path),
                "backup_source": str(backup_source),
                "backup_destination": str(backup_destination) if backup_destination else None,
            }
        )

    log_manifest_path = log_dir / "manifest.json"
    with log_manifest_path.open("w", encoding="utf-8") as handle:
        json.dump({"id": manifest.identifier, "entries": log_entries}, handle, indent=2)

    return log_manifest_path


def rollback_manifest(paths: OrganizerPaths, manifest_id: str) -> None:
    """Rollback the changes recorded in ``manifest_id`` log."""

    log_dir = paths.log_dir / manifest_id
    log_manifest_path = log_dir / "manifest.json"
    if not log_manifest_path.exists():
        raise FileNotFoundError(f"No log manifest for id {manifest_id}")

    with log_manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    for entry in reversed(data.get("entries", [])):
        destination_path = Path(entry["destination_path"])
        backup_destination = entry.get("backup_destination")
        backup_source = Path(entry["backup_source"])
        source_path = Path(entry["source_path"])

        if destination_path.exists():
            destination_path.unlink()

        if backup_destination:
            original_dest = Path(backup_destination)
            if original_dest.exists():
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(original_dest, destination_path)

        if backup_source.exists():
            source_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(backup_source, source_path)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "StageManifest",
    "stage_changes",
    "load_manifest",
    "preview_diff",
    "apply_manifest",
    "rollback_manifest",
]

