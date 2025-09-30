"""Rule DSL parsing and evaluation utilities."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

from .models import (
    FileMetadata,
    Rule,
    RuleAction,
    RuleCondition,
    SuggestedChange,
)


_ACTION_TYPES = {"move", "rename", "tag", "trash"}


class RuleValidationError(ValueError):
    """Raised when a rule definition is invalid."""


def _normalize_tags(tags: Iterable[str] | None) -> tuple[str, ...]:
    if not tags:
        return ()
    return tuple(sorted({tag.strip().lower() for tag in tags if tag.strip()}))


def parse_rule(name: str, raw: Mapping[str, object]) -> Rule:
    """Parse a raw rule mapping into a :class:`Rule`."""

    conditions_data = raw.get("when")
    if not isinstance(conditions_data, Sequence) or not conditions_data:
        raise RuleValidationError(f"Rule '{name}' must define a non-empty 'when' list")

    actions_data = raw.get("actions")
    if not isinstance(actions_data, Sequence) or not actions_data:
        raise RuleValidationError(f"Rule '{name}' must define a non-empty 'actions' list")

    conditions: list[RuleCondition] = []
    for index, condition in enumerate(conditions_data):
        if not isinstance(condition, Mapping):
            raise RuleValidationError(
                f"Rule '{name}' condition {index} must be a mapping, got {type(condition)!r}"
            )
        tags = condition.get("tags")
        conditions.append(
            RuleCondition(
                kind=_optional_str(condition.get("kind")),
                extension=_optional_str(condition.get("extension")),
                source_app=_optional_str(condition.get("sourceApp")),
                domain=_optional_str(condition.get("domain")),
                path_regex=_optional_str(condition.get("path")),
                min_size=_optional_int(condition.get("minSize")),
                max_size=_optional_int(condition.get("maxSize")),
                tags=_normalize_tags(tags if isinstance(tags, Iterable) else None),
            )
        )

    actions: list[RuleAction] = []
    for index, action in enumerate(actions_data):
        if not isinstance(action, Mapping):
            raise RuleValidationError(
                f"Rule '{name}' action {index} must be a mapping, got {type(action)!r}"
            )
        action_type = _optional_str(action.get("type"))
        if not action_type or action_type not in _ACTION_TYPES:
            raise RuleValidationError(
                f"Rule '{name}' action {index} has unsupported type {action.get('type')!r}"
            )

        destination = action.get("destination")
        destination_path: Path | None = None
        if destination is not None:
            destination_path = Path(str(destination)).expanduser()

        actions.append(
            RuleAction(
                type=action_type,
                destination=destination_path,
                rename=_optional_str(action.get("rename")),
                tag=_optional_str(action.get("tag")),
            )
        )

    ask = _optional_str(raw.get("ask"))

    return Rule(name=name, conditions=tuple(conditions), actions=tuple(actions), ask=ask)


def load_rules(definitions: Mapping[str, Mapping[str, object]]) -> list[Rule]:
    """Load multiple rules from a mapping definition."""

    rules: list[Rule] = []
    for name, definition in definitions.items():
        rules.append(parse_rule(name, definition))
    return rules


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise RuleValidationError(f"Expected integer value, got {value!r}") from exc


def rule_matches(rule: Rule, metadata: FileMetadata) -> bool:
    """Return ``True`` if ``rule`` applies to ``metadata``."""

    for condition in rule.conditions:
        if not _condition_matches(condition, metadata):
            return False
    return True


def _condition_matches(condition: RuleCondition, metadata: FileMetadata) -> bool:
    if condition.kind and condition.kind.lower() != (metadata.kind or "").lower():
        return False

    if condition.extension:
        normalized = condition.extension.lower().lstrip(".")
        metadata_ext = metadata.normalized_extension()
        if not metadata_ext or metadata_ext != normalized:
            return False

    if condition.source_app and condition.source_app.lower() != (metadata.source_app or "").lower():
        return False

    if condition.domain and condition.domain.lower() not in (metadata.domain or "").lower():
        return False

    if condition.path_regex:
        pattern = re.compile(condition.path_regex)
        if not pattern.search(str(metadata.path)):
            return False

    if condition.min_size is not None and (metadata.size or 0) < condition.min_size:
        return False

    if condition.max_size is not None and (metadata.size or 0) > condition.max_size:
        return False

    if condition.tags:
        metadata_tags = {tag.lower() for tag in metadata.tags}
        if not set(condition.tags).issubset(metadata_tags):
            return False

    return True


def build_suggestions(
    metadata_list: Sequence[FileMetadata],
    rules: Sequence[Rule],
    *,
    default_destination: Path | None = None,
) -> list[SuggestedChange]:
    """Generate suggestions for ``metadata_list`` using ``rules``."""

    suggestions: list[SuggestedChange] = []
    for metadata in metadata_list:
        for rule in rules:
            if not rule_matches(rule, metadata):
                continue
            for action in rule.actions:
                suggestion = _materialize_action(metadata, rule, action, default_destination)
                if suggestion is not None:
                    suggestions.append(suggestion)
            break  # stop at first matching rule for determinism
    return suggestions


def _materialize_action(
    metadata: FileMetadata,
    rule: Rule,
    action: RuleAction,
    default_destination: Path | None,
) -> SuggestedChange | None:
    if action.type in {"move", "rename"}:
        destination = action.destination or default_destination
        if not destination:
            return None
        if action.rename:
            destination_name = metadata.format_template(action.rename)
            destination = Path(destination) / destination_name
        else:
            destination = Path(destination) / metadata.path.name
        return SuggestedChange(
            rule_name=rule.name,
            source=metadata.path,
            destination=destination,
            action_type=action.type,
        )

    if action.type == "tag":
        # Tags are currently informational; no filesystem change required.
        return SuggestedChange(
            rule_name=rule.name,
            source=metadata.path,
            destination=metadata.path,
            action_type="tag",
        )

    if action.type == "trash":
        return SuggestedChange(
            rule_name=rule.name,
            source=metadata.path,
            destination=metadata.path,
            action_type="trash",
        )

    return None


__all__ = [
    "RuleValidationError",
    "parse_rule",
    "load_rules",
    "rule_matches",
    "build_suggestions",
]

