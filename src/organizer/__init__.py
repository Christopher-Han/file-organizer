"""Core package for the Agentic File Organizer."""

from .config import OrganizerPaths, load_organizer_paths
from .models import FileMetadata, SuggestedChange
from .rules import build_suggestions, load_rules, parse_rule, rule_matches
from .staging import (
    StageManifest,
    apply_manifest,
    load_manifest,
    preview_diff,
    rollback_manifest,
    stage_changes,
)

__all__ = [
    "OrganizerPaths",
    "load_organizer_paths",
    "FileMetadata",
    "SuggestedChange",
    "StageManifest",
    "build_suggestions",
    "load_rules",
    "parse_rule",
    "rule_matches",
    "stage_changes",
    "load_manifest",
    "preview_diff",
    "apply_manifest",
    "rollback_manifest",
]
