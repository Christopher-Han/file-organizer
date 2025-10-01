from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from organizer.config import load_organizer_paths
from organizer.llm import LlamaAPIError, LlamaClient


@dataclass
class StubSDK:
    response: dict[str, object]

    def __post_init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(payload)
        return self.response


class StubFactory:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.created = False
        self.received_key: str | None = None
        self.received_base_url: str | None = None
        self.sdk = StubSDK(response)

    def __call__(self, api_key: str, base_url: str) -> StubSDK:
        self.created = True
        self.received_key = api_key
        self.received_base_url = base_url
        return self.sdk


def build_client(
    tmp_path: Path,
    *,
    factory: StubFactory | None = None,
) -> tuple[LlamaClient, StubFactory | None, Path]:
    paths = load_organizer_paths(tmp_path / "organizer")
    stub_factory = factory
    client = LlamaClient(paths, sdk_factory=stub_factory, allow_env_fallback=False)
    return client, stub_factory, paths.llama_api_key_file


def test_set_api_key_persists(tmp_path: Path) -> None:
    client, _, key_path = build_client(tmp_path)
    client.set_api_key(" secret-key ")
    stored = key_path.read_text(encoding="utf-8")
    assert stored == "secret-key"

    client.clear_cached_key()
    credentials = client.load_credentials()
    assert credentials.api_key == "secret-key"


def test_complete_uses_sdk_factory(tmp_path: Path) -> None:
    response = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "Here you go."},
            }
        ]
    }
    factory = StubFactory(response)
    client, _, _ = build_client(tmp_path, factory=factory)
    client.set_api_key("abc123")

    result = client.complete(
        "Summarize the document.",
        model="llama3-70b-instruct",
        temperature=0.5,
        max_tokens=256,
        extra_params={"top_p": 0.9},
    )

    assert result == "Here you go."
    assert factory.created is True
    assert factory.received_key == "abc123"
    assert factory.received_base_url.endswith("api.llama-api.com")
    assert factory.sdk.calls, "Expected SDK run call"
    payload = factory.sdk.calls[0]
    assert payload["model"] == "llama3-70b-instruct"
    assert payload["messages"][0]["content"] == "Summarize the document."
    assert payload["top_p"] == 0.9


def test_complete_requires_api_key(tmp_path: Path) -> None:
    client, _, _ = build_client(tmp_path)
    with pytest.raises(LlamaAPIError):
        client.complete("Hello")
