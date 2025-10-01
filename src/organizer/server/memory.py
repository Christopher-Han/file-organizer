"""Memory management tool registrations for the MCP server."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Mapping, Sequence

from .app import FileOrganizerServer
from .context import ServerContext


def register_memory_tools(server: FileOrganizerServer) -> None:
    """Register `get_memory`, `update_memory`, and `learn_from_confirmations` tools."""

    @server.tool("get_memory")
    def _get_memory(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        memory = ctx.memory_store.load()
        return {"memory": memory}

    @server.tool("update_memory")
    def _update_memory(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        patch = payload.get("patch") or payload.get("memory")
        if not isinstance(patch, Mapping):
            raise ValueError("update_memory requires a mapping provided via 'patch' or 'memory'")

        current = ctx.memory_store.load()
        merged = _deep_merge(current, patch)
        ctx.memory_store.save(merged)
        return {"memory": merged}

    @server.tool("learn_from_confirmations")
    def _learn(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        confirmations = payload.get("confirmations")
        if confirmations is None or not isinstance(confirmations, Sequence):
            raise ValueError("learn_from_confirmations requires a 'confirmations' sequence")

        current = ctx.memory_store.load()
        preferences = current.setdefault("preferences", {})
        stats = preferences.setdefault("confirmation_stats", {})
        history = preferences.setdefault("confirmation_history", [])

        applied: list[dict[str, Any]] = []
        for entry in confirmations:
            if not isinstance(entry, Mapping):
                raise ValueError("Confirmation entries must be mappings")
            rule_name = entry.get("rule_name") or entry.get("ruleName")
            accepted = entry.get("accepted")
            if not isinstance(rule_name, str) or not rule_name:
                raise ValueError("Confirmation entries require a non-empty 'rule_name'")
            if not isinstance(accepted, bool):
                raise ValueError("Confirmation entries require an 'accepted' boolean")

            record = {
                "rule_name": rule_name,
                "accepted": accepted,
            }
            applied.append(record)

            rule_stats = stats.setdefault(rule_name, {"accepted": 0, "rejected": 0})
            key = "accepted" if accepted else "rejected"
            rule_stats[key] = int(rule_stats.get(key, 0)) + 1

        if applied:
            history.extend(applied)
            if len(history) > 50:
                del history[:-50]
            ctx.memory_store.save(current)

        return {
            "memory": current,
            "applied": applied,
        }


def _deep_merge(base: Mapping[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {key: _copy_value(value) for key, value in base.items()}
    for key, value in patch.items():
        if key in merged and isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = _copy_value(value)
    return merged


def _copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _copy_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return value


__all__ = ["register_memory_tools"]
