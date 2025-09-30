"""Context helpers for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import OrganizerPaths, load_organizer_paths
from ..storage import JsonMemoryStore, SQLiteIndex


@dataclass
class ServerContext:
    """Aggregate shared services used by MCP tool handlers."""

    paths: OrganizerPaths
    memory_store: JsonMemoryStore
    index: SQLiteIndex

    @classmethod
    def from_base_dir(cls, base_dir: Path | None = None) -> "ServerContext":
        paths = load_organizer_paths(base_dir)
        memory_store = JsonMemoryStore(paths.memory_file, default_payload={"rules": [], "preferences": {}})
        index = SQLiteIndex(paths.index_file)
        return cls(paths=paths, memory_store=memory_store, index=index)

    def close(self) -> None:
        """Release resources held by the context."""

        self.index.close()


__all__ = ["ServerContext"]
