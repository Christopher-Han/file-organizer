"""JSON-backed memory persistence for the organizer."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, MutableMapping


class MemoryStoreError(RuntimeError):
    """Raised when the memory store cannot be read or written."""


@dataclass
class JsonMemoryStore:
    """Persist organizer memory data as JSON on disk."""

    path: Path
    default_payload: Mapping[str, Any] = field(default_factory=dict)

    def load(self) -> MutableMapping[str, Any]:
        """Return the stored memory payload."""

        if not self.path.exists():
            return self._fresh_payload()

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover - raise for clarity
            raise MemoryStoreError(f"Invalid memory JSON at {self.path}") from exc

        if not isinstance(data, dict):
            raise MemoryStoreError("Memory payload must be a JSON object")

        return data

    def save(self, payload: Mapping[str, Any]) -> None:
        """Persist ``payload`` atomically."""

        if not isinstance(payload, Mapping):
            raise TypeError("Payload must be a mapping")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")

        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.flush()
        except OSError as exc:  # pragma: no cover - passthrough for context
            raise MemoryStoreError(f"Failed writing temporary memory file {tmp_path}") from exc

        try:
            tmp_path.replace(self.path)
        except OSError as exc:  # pragma: no cover - passthrough for context
            raise MemoryStoreError(f"Failed to move temporary memory file into place: {tmp_path}") from exc

    def _fresh_payload(self) -> MutableMapping[str, Any]:
        return deepcopy(dict(self.default_payload))


__all__ = ["JsonMemoryStore", "MemoryStoreError"]
