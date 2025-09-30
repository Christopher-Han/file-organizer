"""SQLite-backed index utilities."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class SQLiteIndexError(RuntimeError):
    """Raised for SQLite index initialization failures."""


@dataclass
class SQLiteIndex:
    """Manage the SQLite database used for filesystem indexing."""

    path: Path
    _connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Return an initialized SQLite connection."""

        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                connection = sqlite3.connect(self.path)
            except sqlite3.Error as exc:  # pragma: no cover - passthrough for clarity
                raise SQLiteIndexError(f"Failed to open SQLite index at {self.path}") from exc

            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            self._initialize_schema(connection)
            self._connection = connection

        return self._connection

    def close(self) -> None:
        """Close the open connection, if present."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _initialize_schema(self, connection: sqlite3.Connection) -> None:
        """Create tables and triggers required by the index."""

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );

            INSERT OR IGNORE INTO schema_version (id, version) VALUES (1, 1);

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                parent TEXT NOT NULL,
                name TEXT NOT NULL,
                size INTEGER,
                modified_at REAL,
                created_at REAL,
                checksum TEXT
            );

            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                PRIMARY KEY (file_id, tag)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                path,
                name,
                content='files',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, path, name) VALUES (new.id, new.path, new.name);
            END;

            CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, name) VALUES('delete', old.id, old.path, old.name);
            END;

            CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, path, name) VALUES('delete', old.id, old.path, old.name);
                INSERT INTO files_fts(rowid, path, name) VALUES (new.id, new.path, new.name);
            END;
            """
        )
        connection.commit()

    def vacuum(self) -> None:
        """Run SQLite maintenance to keep the index compact."""

        connection = self.connect()
        connection.execute("VACUUM")

    def pragma_settings(self) -> dict[str, str]:
        """Return key pragma values useful for diagnostics."""

        connection = self.connect()
        values = {}
        for pragma in self._diagnostic_pragmas():
            cursor = connection.execute(f"PRAGMA {pragma};")
            values[pragma] = str(cursor.fetchone()[0])
        return values

    @staticmethod
    def _diagnostic_pragmas() -> Iterable[str]:
        return ("journal_mode", "foreign_keys")


__all__ = ["SQLiteIndex", "SQLiteIndexError"]
