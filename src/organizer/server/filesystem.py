"""Filesystem tool registrations for the File Organizer MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping, Sequence

from ..indexing import ScanError, scan_paths
from ..storage import IndexedFile
from .app import FileOrganizerServer
from .context import ServerContext


def register_filesystem_tools(server: FileOrganizerServer) -> None:
    """Register filesystem scanning, indexing, and search tools."""

    @server.tool("scan_paths")
    def _scan(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        paths = _parse_paths(payload.get("paths"))
        if not paths:
            raise ValueError("scan_paths requires a non-empty 'paths' collection")

        include_hidden = _coerce_bool(
            payload.get("include_hidden", payload.get("includeHidden")), default=False
        )
        follow_symlinks = _coerce_bool(
            payload.get("follow_symlinks", payload.get("followSymlinks")), default=False
        )
        max_depth = _coerce_int(
            payload.get("max_depth", payload.get("maxDepth")),
            name="max_depth",
            minimum=0,
            default=None,
        )
        compute_checksums = _coerce_bool(
            payload.get("checksums", payload.get("computeChecksums")), default=False
        )

        entries, errors = scan_paths(
            paths,
            include_hidden=include_hidden,
            follow_symlinks=follow_symlinks,
            max_depth=max_depth,
            compute_checksums=compute_checksums,
        )

        return {
            "entries": [_serialize_indexed_file(entry) for entry in entries],
            "stats": {"scanned": len(entries), "errors": len(errors)},
            "errors": [_serialize_error(error) for error in errors],
        }

    @server.tool("index_paths")
    def _index(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        paths = _parse_paths(payload.get("paths"))
        if not paths:
            raise ValueError("index_paths requires a non-empty 'paths' collection")

        include_hidden = _coerce_bool(
            payload.get("include_hidden", payload.get("includeHidden")), default=False
        )
        follow_symlinks = _coerce_bool(
            payload.get("follow_symlinks", payload.get("followSymlinks")), default=False
        )
        max_depth = _coerce_int(
            payload.get("max_depth", payload.get("maxDepth")),
            name="max_depth",
            minimum=0,
            default=None,
        )
        compute_checksums = _coerce_bool(
            payload.get("checksums", payload.get("computeChecksums")), default=False
        )
        prune = _coerce_bool(payload.get("prune"), default=False)

        entries, errors = scan_paths(
            paths,
            include_hidden=include_hidden,
            follow_symlinks=follow_symlinks,
            max_depth=max_depth,
            compute_checksums=compute_checksums,
        )

        indexed = ctx.index.upsert_files(entries)
        pruned = ctx.index.purge_missing(paths) if prune else 0

        return {
            "indexed": indexed,
            "pruned": pruned,
            "errors": [_serialize_error(error) for error in errors],
            "stats": {"scanned": len(entries), "indexed": indexed, "errors": len(errors)},
        }

    @server.tool("search_files")
    def _search(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        query = payload.get("query")
        if not isinstance(query, str):
            raise ValueError("search_files requires a 'query' string")

        limit = _coerce_int(payload.get("limit"), name="limit", minimum=1, maximum=1000, default=50)
        use_fts = _coerce_bool(payload.get("use_fts", payload.get("useFts")), default=True)

        results = ctx.index.search(query, limit=limit, use_fts=use_fts)
        for row in results:
            # Convert tuple tags to lists for JSON serialization.
            row["tags"] = list(row.get("tags", ()))

        return {"results": results, "count": len(results)}


def _parse_paths(raw: Any) -> list[Path]:
    if raw is None:
        return []
    if isinstance(raw, (str, Path)):
        raw = [raw]
    if not isinstance(raw, Sequence):
        raise ValueError("paths must be a string or a sequence of strings")

    paths: list[Path] = []
    for item in raw:
        if not isinstance(item, (str, Path)):
            raise ValueError("paths must contain only string values")
        paths.append(Path(item))
    return paths


def _serialize_indexed_file(entry: IndexedFile) -> dict[str, Any]:
    return {
        "path": str(entry.path),
        "parent": str(entry.path.parent),
        "name": entry.path.name,
        "size": entry.size,
        "modified_at": entry.modified_at,
        "created_at": entry.created_at,
        "checksum": entry.checksum,
        "tags": list(entry.tags),
    }


def _serialize_error(error: ScanError) -> dict[str, str]:
    return {"path": str(error.path), "message": error.message}


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ValueError("Expected a boolean-compatible value")


def _coerce_int(
    value: Any,
    *,
    name: str,
    minimum: int | None = None,
    maximum: int | None = None,
    default: int | None = None,
) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"{name} must be an integer") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return number


__all__ = ["register_filesystem_tools"]
