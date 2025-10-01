"""Rule and staging tool registrations for the MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from ..models import FileMetadata, SuggestedChange
from ..rules import Rule, RuleValidationError, build_suggestions, parse_rule
from ..staging import (
    StageManifest,
    apply_manifest as apply_stage_manifest,
    load_manifest,
    preview_diff as preview_stage_diff,
    rollback_manifest as rollback_stage_manifest,
    stage_changes,
)
from .app import FileOrganizerServer
from .context import ServerContext


def register_rule_tools(server: FileOrganizerServer) -> None:
    """Register rule evaluation and staging tools on ``server``."""

    @server.tool("suggest_organization")
    def _suggest(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        metadata = _parse_metadata(payload.get("files"))
        if not metadata:
            raise ValueError("suggest_organization requires a non-empty 'files' list")

        use_memory = _coerce_bool(payload.get("use_memory_rules"), default=True)
        rules = _gather_rules(payload.get("rules"), ctx, use_memory=use_memory)
        if not rules:
            return {"suggestions": [], "count": 0}

        default_destination = payload.get("default_destination")
        default_path = Path(default_destination).expanduser() if default_destination else None

        suggestions = build_suggestions(metadata, rules, default_destination=default_path)
        return {
            "suggestions": [_serialize_suggestion(item) for item in suggestions],
            "count": len(suggestions),
        }

    @server.tool("stage_changes")
    def _stage(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        suggestions = _parse_suggestions(payload.get("suggestions"))
        if not suggestions:
            raise ValueError("stage_changes requires a non-empty 'suggestions' list")

        manifest_id = payload.get("manifest_id")
        manifest = stage_changes(suggestions, ctx.paths, manifest_id=manifest_id)
        return _serialize_manifest(manifest)

    @server.tool("preview_diff")
    def _preview(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        manifest_id = payload.get("manifest_id")
        if not isinstance(manifest_id, str) or not manifest_id:
            raise ValueError("preview_diff requires a 'manifest_id' string")

        manifest = load_manifest(ctx.paths, manifest_id)
        return {
            "manifest_id": manifest.identifier,
            "preview": preview_stage_diff(manifest),
        }

    @server.tool("apply_manifest")
    def _apply(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        manifest_id = payload.get("manifest_id")
        if not isinstance(manifest_id, str) or not manifest_id:
            raise ValueError("apply_manifest requires a 'manifest_id' string")

        manifest = load_manifest(ctx.paths, manifest_id)
        log_path = apply_stage_manifest(ctx.paths, manifest)
        return {
            "manifest_id": manifest.identifier,
            "log_path": str(log_path),
        }

    @server.tool("rollback_manifest")
    def _rollback(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        manifest_id = payload.get("manifest_id")
        if not isinstance(manifest_id, str) or not manifest_id:
            raise ValueError("rollback_manifest requires a 'manifest_id' string")

        rollback_stage_manifest(ctx.paths, manifest_id)
        return {"manifest_id": manifest_id}


def _parse_metadata(raw: Any) -> list[FileMetadata]:
    if raw is None:
        return []
    if not isinstance(raw, Sequence):
        raise ValueError("files must be provided as a sequence")

    items: list[FileMetadata] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError("Each file entry must be a mapping")
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            raise ValueError("File entries require a 'path' string")

        path = Path(path_value).expanduser()
        tags = entry.get("tags") if isinstance(entry.get("tags"), Sequence) else ()

        items.append(
            FileMetadata(
                path=path,
                kind=entry.get("kind"),
                extension=entry.get("extension"),
                source_app=entry.get("source_app") or entry.get("sourceApp"),
                domain=entry.get("domain"),
                size=entry.get("size"),
                tags=tuple(str(tag) for tag in tags if isinstance(tag, str)),
            )
        )
    return items


def _gather_rules(raw_rules: Any, ctx: ServerContext, *, use_memory: bool) -> list[Rule]:
    parsed: dict[str, Rule] = {}

    if use_memory:
        memory_payload = ctx.memory_store.load()
        memory_rules = memory_payload.get("rules", [])
        for name, definition in _iter_rule_definitions(memory_rules):
            try:
                parsed[name] = parse_rule(name, definition)
            except RuleValidationError as exc:
                raise ValueError(f"Invalid rule '{name}': {exc}") from exc

    for name, definition in _iter_rule_definitions(raw_rules):
        try:
            parsed[name] = parse_rule(name, definition)
        except RuleValidationError as exc:
            raise ValueError(f"Invalid rule '{name}': {exc}") from exc

    return list(parsed.values())


def _iter_rule_definitions(raw: Any) -> list[tuple[str, Mapping[str, Any]]]:
    if raw is None:
        return []

    results: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(raw, Mapping):
        for name, definition in raw.items():
            if not isinstance(definition, Mapping):
                raise ValueError("Rule definitions must be mappings")
            results.append((str(name), definition))
    elif isinstance(raw, Sequence):
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("Rule list entries must be mappings")
            name = entry.get("name")
            definition = entry.get("definition") or entry.get("rule")
            if not isinstance(name, str) or not name:
                raise ValueError("Rule entries require a non-empty 'name'")
            if not isinstance(definition, Mapping):
                raise ValueError("Rule entries require a 'definition' mapping")
            results.append((name, definition))
    else:
        raise ValueError("rules must be provided as a sequence or mapping")

    return results


def _parse_suggestions(raw: Any) -> list[SuggestedChange]:
    if raw is None or not isinstance(raw, Sequence):
        return []

    suggestions: list[SuggestedChange] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError("Suggestions must be objects with suggestion metadata")
        rule_name = entry.get("rule_name") or entry.get("ruleName")
        source = entry.get("source")
        destination = entry.get("destination")
        action_type = entry.get("action_type") or entry.get("actionType")
        if not all(isinstance(value, str) and value for value in (rule_name, source, destination, action_type)):
            raise ValueError("Each suggestion must include rule_name, source, destination, and action_type")
        suggestions.append(
            SuggestedChange(
                rule_name=str(rule_name),
                source=Path(source).expanduser(),
                destination=Path(destination).expanduser(),
                action_type=str(action_type),
            )
        )
    return suggestions


def _serialize_suggestion(suggestion: SuggestedChange) -> dict[str, Any]:
    return {
        "rule_name": suggestion.rule_name,
        "source": str(suggestion.source),
        "destination": str(suggestion.destination),
        "action_type": suggestion.action_type,
    }


def _serialize_manifest(manifest: StageManifest) -> dict[str, Any]:
    return {
        "manifest_id": manifest.identifier,
        "path": str(manifest.path),
        "entries": [
            {
                "action": entry.action,
                "source_path": str(entry.source_path),
                "destination_path": str(entry.destination_path),
                "checksum": entry.checksum,
                "staged_relpath": entry.staged_relpath,
            }
            for entry in manifest.entries
        ],
    }


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


__all__ = ["register_rule_tools"]
