from pathlib import Path

from organizer.models import SuggestedChange
from organizer.runtime import PromptContext, build_review_prompt


def test_prompt_uses_memory_preferences(tmp_path: Path) -> None:
    suggestion = SuggestedChange(
        rule_name="Move text",
        source=tmp_path / "notes.txt",
        destination=tmp_path / "archive" / "notes.txt",
        action_type="move",
    )
    memory = {"preferences": {"user_name": "Chris", "tone": "concise", "batch_confirm": True}}

    prompt = build_review_prompt([suggestion], memory=memory)
    assert "Hello Chris" in prompt
    assert "MOVE notes.txt" in prompt
    assert "batch" in prompt.lower()


def test_prompt_truncation_and_context_defaults(tmp_path: Path) -> None:
    suggestions = [
        {
            "rule_name": f"Rule {index}",
            "action_type": "rename",
            "source": f"file{index}.txt",
            "destination": f"file{index}_renamed.txt",
        }
        for index in range(12)
    ]

    prompt = build_review_prompt(suggestions, context=PromptContext(max_preview_items=3))
    assert prompt.count("-") == 4  # 3 entries + truncated notice
    assert "truncated" in prompt
