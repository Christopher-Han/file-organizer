from pathlib import Path

import pytest

from organizer.storage import JsonMemoryStore, MemoryStoreError


def test_load_returns_default_for_missing_file(tmp_path: Path) -> None:
    store = JsonMemoryStore(tmp_path / "memory.json", default_payload={"rules": []})
    payload = store.load()
    assert payload == {"rules": []}


def test_save_and_reload_roundtrip(tmp_path: Path) -> None:
    store = JsonMemoryStore(tmp_path / "memory.json")
    payload = {"rules": ["move"], "preferences": {"confirm": True}}
    store.save(payload)
    reloaded = store.load()
    assert reloaded == payload


def test_invalid_json_raises(tmp_path: Path) -> None:
    memory_file = tmp_path / "memory.json"
    memory_file.write_text("not json", encoding="utf-8")
    store = JsonMemoryStore(memory_file)
    with pytest.raises(MemoryStoreError):
        store.load()


def test_non_mapping_payload_rejected(tmp_path: Path) -> None:
    store = JsonMemoryStore(tmp_path / "memory.json")
    with pytest.raises(TypeError):
        store.save([1, 2, 3])  # type: ignore[arg-type]
