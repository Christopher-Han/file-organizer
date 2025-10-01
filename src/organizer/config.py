"""Configuration utilities for the Agentic File Organizer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_MEMORY_FILENAME = "organizer.memory.json"
DEFAULT_INDEX_FILENAME = "organizer.index.sqlite"
DEFAULT_WORK_DIR = Path.home() / ".organizer"
DEFAULT_STAGING_DIRNAME = "staging"
DEFAULT_LOG_DIRNAME = "logs"
DEFAULT_LLAMA_KEY_FILENAME = "llama.api.key"


@dataclass(frozen=True)
class OrganizerPaths:
    """Resolved filesystem paths used by the organizer."""

    root: Path
    memory_file: Path
    index_file: Path
    staging_dir: Path
    log_dir: Path
    llama_api_key_file: Path

    def iter_ensure_dirs(self) -> Iterable[Path]:
        """Yield directories that should exist for the organizer.

        The caller is responsible for creating the directories. This function simply
        enumerates them, enabling deterministic directory creation order during
        initialization and testing.
        """

        yield self.root
        yield self.staging_dir
        yield self.log_dir


def load_organizer_paths(base_dir: Path | None = None) -> OrganizerPaths:
    """Load organizer paths relative to ``base_dir``.

    Args:
        base_dir: Optional root directory to use instead of ``DEFAULT_WORK_DIR``.

    Returns:
        An :class:`OrganizerPaths` instance with directories created if they were
        missing.
    """

    root_dir = (base_dir or DEFAULT_WORK_DIR).expanduser().resolve()
    memory_file = root_dir / DEFAULT_MEMORY_FILENAME
    index_file = root_dir / DEFAULT_INDEX_FILENAME
    staging_dir = root_dir / DEFAULT_STAGING_DIRNAME
    log_dir = root_dir / DEFAULT_LOG_DIRNAME
    llama_api_key_file = root_dir / DEFAULT_LLAMA_KEY_FILENAME

    paths = OrganizerPaths(
        root=root_dir,
        memory_file=memory_file,
        index_file=index_file,
        staging_dir=staging_dir,
        log_dir=log_dir,
        llama_api_key_file=llama_api_key_file,
    )

    for directory in paths.iter_ensure_dirs():
        directory.mkdir(parents=True, exist_ok=True)

    return paths


__all__ = ["OrganizerPaths", "load_organizer_paths"]
