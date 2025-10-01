"""Filesystem scanning and indexing helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Sequence

from .storage import IndexedFile


@dataclass(frozen=True)
class ScanError:
    """Represents a failure encountered during filesystem scanning."""

    path: Path
    message: str


def scan_paths(
    paths: Sequence[Path | str],
    *,
    include_hidden: bool = False,
    follow_symlinks: bool = False,
    max_depth: int | None = None,
    compute_checksums: bool = False,
) -> tuple[list[IndexedFile], list[ScanError]]:
    """Walk ``paths`` and collect metadata for files discovered."""

    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth must be non-negative when provided")

    results: list[IndexedFile] = []
    errors: list[ScanError] = []
    visited: set[str] = set()

    for raw in paths:
        base = Path(raw).expanduser()
        resolved = base.resolve(strict=False)
        key = str(resolved)
        if key in visited:
            continue
        visited.add(key)

        if not resolved.exists():
            errors.append(ScanError(path=resolved, message="Path does not exist"))
            continue

        if resolved.is_dir():
            results.extend(
                _scan_directory(
                    resolved,
                    include_hidden=include_hidden,
                    follow_symlinks=follow_symlinks,
                    max_depth=max_depth,
                    compute_checksums=compute_checksums,
                    errors=errors,
                )
            )
        elif resolved.is_file():
            record = _scan_file(resolved, compute_checksums=compute_checksums, errors=errors)
            if record is not None:
                results.append(record)
        else:
            errors.append(ScanError(path=resolved, message="Unsupported filesystem entry"))

    results.sort(key=lambda entry: str(entry.path))
    errors.sort(key=lambda error: str(error.path))
    return results, errors


def _scan_directory(
    base_path: Path,
    *,
    include_hidden: bool,
    follow_symlinks: bool,
    max_depth: int | None,
    compute_checksums: bool,
    errors: list[ScanError],
) -> list[IndexedFile]:
    entries: list[IndexedFile] = []

    def _on_error(exc: OSError) -> None:
        target = getattr(exc, "filename", None)
        error_path = Path(target) if target else base_path
        errors.append(ScanError(path=error_path, message=str(exc)))

    for root, dirnames, filenames in os.walk(base_path, followlinks=follow_symlinks, onerror=_on_error):
        root_path = Path(root)
        depth = 0 if root_path == base_path else len(root_path.relative_to(base_path).parts)

        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []

        if not include_hidden:
            dirnames[:] = [name for name in dirnames if not _is_hidden(root_path / name)]

        for name in filenames:
            file_path = root_path / name
            if not include_hidden and _is_hidden(file_path):
                continue
            record = _scan_file(file_path, compute_checksums=compute_checksums, errors=errors)
            if record is not None:
                entries.append(record)

    return entries


def _scan_file(path: Path, *, compute_checksums: bool, errors: list[ScanError]) -> IndexedFile | None:
    try:
        stat_result = path.stat()
    except OSError as exc:
        errors.append(ScanError(path=path, message=str(exc)))
        return None

    checksum = _file_checksum(path) if compute_checksums else None

    return IndexedFile(
        path=path.resolve(),
        size=stat_result.st_size,
        modified_at=stat_result.st_mtime,
        created_at=stat_result.st_ctime,
        checksum=checksum,
    )


def _is_hidden(path: Path) -> bool:
    for part in path.parts:
        if part in {"", ".", "..", path.anchor}:
            continue
        if part.startswith('.'):
            return True
    return False


def _file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["ScanError", "scan_paths"]
