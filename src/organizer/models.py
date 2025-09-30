"""Core dataclasses shared across the file organizer modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence


@dataclass(frozen=True)
class FileMetadata:
    """Representation of a file inspected by the organizer."""

    path: Path
    kind: Optional[str] = None
    extension: Optional[str] = None
    source_app: Optional[str] = None
    domain: Optional[str] = None
    size: Optional[int] = None
    tags: Sequence[str] = field(default_factory=tuple)

    def normalized_extension(self) -> Optional[str]:
        """Return the extension without the leading dot."""

        if not self.extension:
            return None
        ext = self.extension.lower().lstrip(".")
        return ext or None

    def format_template(self, template: str) -> str:
        """Format ``template`` using file metadata values."""

        context = {
            "name": self.path.stem,
            "ext": self.normalized_extension() or "",
            "kind": self.kind or "",
            "source_app": self.source_app or "",
            "domain": self.domain or "",
            "size": self.size or 0,
        }
        return template.format(**context)


@dataclass(frozen=True)
class RuleCondition:
    """Conditions that determine whether a rule applies to a file."""

    kind: Optional[str] = None
    extension: Optional[str] = None
    source_app: Optional[str] = None
    domain: Optional[str] = None
    path_regex: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    tags: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuleAction:
    """Action to take when a rule matches."""

    type: str
    destination: Optional[Path] = None
    rename: Optional[str] = None
    tag: Optional[str] = None


@dataclass(frozen=True)
class Rule:
    """Rule combining conditions and actions."""

    name: str
    conditions: Sequence[RuleCondition]
    actions: Sequence[RuleAction]
    ask: Optional[str] = None


@dataclass(frozen=True)
class SuggestedChange:
    """Materialized change proposal produced by the suggestion engine."""

    rule_name: str
    source: Path
    destination: Path
    action_type: str


def iter_extensions(path: Path) -> Iterable[str]:
    """Yield extensions of ``path`` for matching heuristics."""

    suffix = path.suffix.lower().lstrip(".")
    if suffix:
        yield suffix

