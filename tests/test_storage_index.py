from pathlib import Path

from organizer.storage import SQLiteIndex


def test_index_initializes_schema(tmp_path: Path) -> None:
    index_path = tmp_path / "index" / "organizer.sqlite"
    index = SQLiteIndex(index_path)
    connection = index.connect()

    cursor = connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view', 'virtual table')"
    )
    names = {row[0] for row in cursor.fetchall()}
    assert {"files", "file_tags", "files_fts", "schema_version"}.issubset(names)

    pragma = connection.execute("PRAGMA journal_mode;").fetchone()[0]
    assert pragma.lower() == "wal"

    index.close()


def test_index_reuses_connection(tmp_path: Path) -> None:
    index = SQLiteIndex(tmp_path / "index.sqlite")
    connection_one = index.connect()
    connection_two = index.connect()
    assert connection_one is connection_two
    index.close()


def test_vacuum_runs(tmp_path: Path) -> None:
    index = SQLiteIndex(tmp_path / "index.sqlite")
    index.connect()
    index.vacuum()
    index.close()
