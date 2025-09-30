"""Tests for the rule DSL and suggestion builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from organizer.models import FileMetadata
from organizer.rules import RuleValidationError, build_suggestions, load_rules, parse_rule


def test_parse_rule_requires_conditions():
    with pytest.raises(RuleValidationError):
        parse_rule("invalid", {"actions": [{"type": "move", "destination": "/tmp"}]})


def test_parse_rule_requires_actions():
    with pytest.raises(RuleValidationError):
        parse_rule("invalid", {"when": [{"extension": "pdf"}]})


def test_build_suggestions_with_destination(tmp_path: Path) -> None:
    rule_definitions = {
        "Move PDFs": {
            "when": [{"extension": "pdf"}],
            "actions": [{"type": "move", "destination": str(tmp_path)}],
        }
    }

    rules = load_rules(rule_definitions)
    metadata = [
        FileMetadata(path=Path("/downloads/report.pdf"), extension="pdf"),
        FileMetadata(path=Path("/downloads/image.png"), extension="png"),
    ]

    suggestions = build_suggestions(metadata, rules)
    assert len(suggestions) == 1
    assert suggestions[0].destination == tmp_path / "report.pdf"


def test_build_suggestions_uses_rename(tmp_path: Path) -> None:
    rule_definitions = {
        "Rename": {
            "when": [{"extension": "jpg"}],
            "actions": [
                {
                    "type": "rename",
                    "destination": str(tmp_path),
                    "rename": "image_{kind}.jpg",
                }
            ],
        }
    }

    rules = load_rules(rule_definitions)
    metadata = [
        FileMetadata(path=Path("/downloads/photo.jpg"), extension="jpg", kind="image"),
    ]

    suggestions = build_suggestions(metadata, rules)
    assert suggestions
    assert suggestions[0].destination == tmp_path / "image_image.jpg"

