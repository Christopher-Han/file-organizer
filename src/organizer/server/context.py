"""Context helpers for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import OrganizerPaths, load_organizer_paths
from ..storage import JsonMemoryStore, SQLiteIndex
from ..llm import LlamaClient


@dataclass
class ServerContext:
    """Aggregate shared services used by MCP tool handlers."""

    paths: OrganizerPaths
    memory_store: JsonMemoryStore
    index: SQLiteIndex
    llm_client: LlamaClient

    @classmethod
    def from_base_dir(cls, base_dir: Path | None = None) -> "ServerContext":
        paths = load_organizer_paths(base_dir)
        memory_store = JsonMemoryStore(paths.memory_file, default_payload={"rules": [], "preferences": {}})
        index = SQLiteIndex(paths.index_file)
        llm_client = LlamaClient(paths)
        return cls(paths=paths, memory_store=memory_store, index=index, llm_client=llm_client)

    def close(self) -> None:
        """Release resources held by the context."""

        self.index.close()


__all__ = ["ServerContext"]
