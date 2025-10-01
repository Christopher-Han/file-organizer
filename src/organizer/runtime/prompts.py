"""Prompt generation helpers for the organizer runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..models import SuggestedChange


@dataclass(frozen=True)
class PromptContext:
    """Context used when rendering agent prompts."""

    user_name: str | None = None
    tone: str = "friendly"
    prefer_batch_confirm: bool = False
    max_preview_items: int = 10


def build_review_prompt(
    suggestions: Sequence[SuggestedChange | Mapping[str, object]],
    *,
    memory: Mapping[str, object] | None = None,
    context: PromptContext | None = None,
) -> str:
    """Return a prompt guiding the Llama model through review/confirmation."""

    preferences = (memory or {}).get("preferences", {}) if memory else {}
    ctx = context or PromptContext(
        user_name=_coerce_str(preferences.get("user_name")),
        tone=_coerce_str(preferences.get("tone")) or "friendly",
        prefer_batch_confirm=bool(preferences.get("batch_confirm")),
        max_preview_items=_coerce_int(preferences.get("max_preview_items"), default=10),
    )

    header = _build_header(ctx)
    summary_lines = _summarize_suggestions(suggestions, max_items=ctx.max_preview_items)
    guardrails = _GUARDRAIL_TEXT

    prompt_lines = [header, "", "Suggested changes:"]
    prompt_lines.extend(f"- {line}" for line in summary_lines)
    prompt_lines.extend(["", guardrails])
    return "\n".join(prompt_lines)


def _build_header(ctx: PromptContext) -> str:
    greeting = "Hello" if not ctx.user_name else f"Hello {ctx.user_name}"  # pragma: no cover - trivial branch
    tone = ctx.tone.capitalize()
    confirm_text = (
        "Request a single yes/no confirmation for the whole batch."
        if ctx.prefer_batch_confirm
        else "Seek confirmation per file unless the user opts into a batch apply."
    )
    return f"{greeting}! Use a {tone.lower()} tone. {confirm_text}"


def _summarize_suggestions(
    suggestions: Iterable[SuggestedChange | Mapping[str, object]],
    *,
    max_items: int,
) -> list[str]:
    summary: list[str] = []
    for index, suggestion in enumerate(suggestions):
        if index >= max_items:
            summary.append("(additional changes truncated)")
            break
        if isinstance(suggestion, SuggestedChange):
            action = suggestion.action_type.upper()
            summary.append(f"{action} {suggestion.source.name} -> {suggestion.destination}")
        else:
            action = str(suggestion.get("action_type") or suggestion.get("actionType") or "change").upper()
            source = suggestion.get("source") or suggestion.get("path")
            destination = suggestion.get("destination") or "(unchanged)"
            summary.append(f"{action} {source} -> {destination}")
    if not summary:
        summary.append("No actionable changes were suggested.")
    return summary


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_GUARDRAIL_TEXT = (
    "Always describe the staging step before applying changes, present diff highlights, "
    "and remind the user that rollback is available."
)


__all__ = ["PromptContext", "build_review_prompt"]
