"""SQLite-backed index utilities."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class SQLiteIndexError(RuntimeError):
    """Raised for SQLite index initialization failures."""


@dataclass(frozen=True)
class IndexedFile:
    """Filesystem entry persisted in the SQLite index."""

    path: Path
    size: int | None = None
    modified_at: float | None = None
    created_at: float | None = None
    checksum: str | None = None
    tags: Sequence[str] = ()


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

    def upsert_files(self, records: Iterable[IndexedFile]) -> int:
        """Insert or update ``records`` in the index."""

        rows: list[tuple[str, str, str, int | None, float | None, float | None, str | None]] = []
        tag_reset_paths: set[str] = set()
        tag_rows: list[tuple[str, str]] = []

        for record in records:
            path_str = str(record.path)
            rows.append(
                (
                    path_str,
                    str(record.path.parent),
                    record.path.name,
                    record.size,
                    record.modified_at,
                    record.created_at,
                    record.checksum,
                )
            )

            normalized_tags = _normalize_tags(record.tags)
            tag_reset_paths.add(path_str)
            if normalized_tags:
                tag_rows.extend((path_str, tag) for tag in normalized_tags)

        if not rows:
            return 0

        connection = self.connect()
        with connection:
            connection.executemany(
                """
                INSERT INTO files(path, parent, name, size, modified_at, created_at, checksum)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    parent=excluded.parent,
                    name=excluded.name,
                    size=excluded.size,
                    modified_at=excluded.modified_at,
                    created_at=excluded.created_at,
                    checksum=excluded.checksum
                """,
                rows,
            )

            if tag_reset_paths:
                connection.executemany(
                    "DELETE FROM file_tags WHERE file_id = (SELECT id FROM files WHERE path = ?)",
                    ((path,) for path in sorted(tag_reset_paths))
                )

            if tag_rows:
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO file_tags(file_id, tag)
                    VALUES ((SELECT id FROM files WHERE path = ?), ?)
                    """,
                    tag_rows,
                )

        return len(rows)

    def purge_missing(self, roots: Iterable[Path]) -> int:
        """Remove index entries under ``roots`` no longer present on disk."""

        connection = self.connect()
        missing_ids: set[int] = set()
        checked_paths: set[str] = set()

        sentinel = "__organizer_child__"
        for root in roots:
            root_path = Path(root).expanduser().resolve(strict=False)
            root_str = str(root_path)
            child_prefix = str(root_path / sentinel)
            if not child_prefix.endswith(sentinel):
                child_prefix = f"{child_prefix}{sentinel}"
            child_prefix = child_prefix[: -len(sentinel)]
            like_pattern = f"{_escape_like(child_prefix)}%"
            cursor = connection.execute(
                """
                SELECT id, path FROM files
                WHERE path = ? OR path LIKE ? ESCAPE '|'
                """,
                (root_str, like_pattern),
            )
            for row in cursor:
                path_str = row["path"]
                if path_str in checked_paths:
                    continue
                checked_paths.add(path_str)
                if not Path(path_str).exists():
                    missing_ids.add(int(row["id"]))

        if not missing_ids:
            return 0

        with connection:
            connection.executemany(
                "DELETE FROM files WHERE id = ?",
                ((file_id,) for file_id in missing_ids),
            )

        return len(missing_ids)

    def search(self, query: str, *, limit: int = 50, use_fts: bool = True) -> list[dict[str, object]]:
        """Search the index using ``query`` and return matching records."""

        query_text = query.strip()
        if not query_text:
            raise ValueError("Query must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be positive")

        connection = self.connect()
        if use_fts:
            try:
                cursor = connection.execute(
                    """
                    SELECT
                        f.path,
                        f.parent,
                        f.name,
                        f.size,
                        f.modified_at,
                        f.created_at,
                        COALESCE(GROUP_CONCAT(t.tag, ','), '') AS tags,
                        bm25(files_fts) AS score
                    FROM files_fts
                    JOIN files f ON f.id = files_fts.rowid
                    LEFT JOIN file_tags t ON t.file_id = f.id
                    WHERE files_fts MATCH ?
                    GROUP BY f.id
                    ORDER BY score
                    LIMIT ?
                    """,
                    (query_text, limit),
                )
            except sqlite3.OperationalError:
                cursor = connection.execute(
                    """
                    SELECT
                        f.path,
                        f.parent,
                        f.name,
                        f.size,
                        f.modified_at,
                        f.created_at,
                        COALESCE(GROUP_CONCAT(t.tag, ','), '') AS tags,
                        NULL AS score
                    FROM files_fts
                    JOIN files f ON f.id = files_fts.rowid
                    LEFT JOIN file_tags t ON t.file_id = f.id
                    WHERE files_fts MATCH ?
                    GROUP BY f.id
                    ORDER BY f.modified_at IS NULL, f.modified_at DESC, f.name
                    LIMIT ?
                    """,
                    (query_text, limit),
                )
        else:
            like_term = f"%{_escape_like(query_text)}%"
            cursor = connection.execute(
                """
                SELECT
                    f.path,
                    f.parent,
                    f.name,
                    f.size,
                    f.modified_at,
                    f.created_at,
                    COALESCE(GROUP_CONCAT(t.tag, ','), '') AS tags,
                    NULL AS score
                FROM files f
                LEFT JOIN file_tags t ON t.file_id = f.id
                WHERE f.path LIKE ? ESCAPE '|' OR f.name LIKE ? ESCAPE '|'
                GROUP BY f.id
                ORDER BY f.modified_at IS NULL, f.modified_at DESC, f.name
                LIMIT ?
                """,
                (like_term, like_term, limit),
            )

        results: list[dict[str, object]] = []
        for row in cursor.fetchall():
            tags_value = row["tags"]
            tags = tuple(tag for tag in tags_value.split(",") if tag) if tags_value else ()
            results.append(
                {
                    "path": row["path"],
                    "parent": row["parent"],
                    "name": row["name"],
                    "size": row["size"],
                    "modified_at": row["modified_at"],
                    "created_at": row["created_at"],
                    "tags": tags,
                    "score": row["score"],
                }
            )

        return results

    @staticmethod
    def _diagnostic_pragmas() -> Iterable[str]:
        return ("journal_mode", "foreign_keys")


def _normalize_tags(tags: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return tuple(normalized)


def _escape_like(value: str) -> str:
    return value.replace("|", "||").replace("%", "|%").replace("_", "|_")


__all__ = ["IndexedFile", "SQLiteIndex", "SQLiteIndexError"]
