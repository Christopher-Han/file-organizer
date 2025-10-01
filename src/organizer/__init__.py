"""Core package for the Agentic File Organizer."""

from .config import OrganizerPaths, load_organizer_paths
from .models import FileMetadata, SuggestedChange
from .rules import build_suggestions, load_rules, parse_rule, rule_matches
from .runtime import PromptContext, build_review_prompt
from .staging import (
    StageManifest,
    apply_manifest,
    load_manifest,
    preview_diff,
    rollback_manifest,
    stage_changes,
)
from .llm import DEFAULT_MODEL, LlamaAPIError, LlamaClient, LlamaCredentials

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
    "build_review_prompt",
    "PromptContext",
    "stage_changes",
    "load_manifest",
    "preview_diff",
    "apply_manifest",
    "rollback_manifest",
    "DEFAULT_MODEL",
    "LlamaAPIError",
    "LlamaClient",
    "LlamaCredentials",
]
