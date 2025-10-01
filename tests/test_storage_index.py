from dataclasses import replace
from pathlib import Path

import pytest

from organizer.indexing import scan_paths
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


def test_upsert_search_and_purge(tmp_path: Path) -> None:
    base = tmp_path / "docs"
    base.mkdir()
    file_alpha = base / "alpha.txt"
    file_alpha.write_text("alpha contents")
    file_beta = base / "beta.txt"
    file_beta.write_text("beta contents")

    records, errors = scan_paths([base])
    assert errors == []

    tagged_records = [
        replace(record, tags=("Reports", "work")) if record.path == file_alpha.resolve() else record
        for record in records
    ]

    index = SQLiteIndex(tmp_path / "index.sqlite")
    indexed = index.upsert_files(tagged_records)
    assert indexed == len(tagged_records)

    like_results = index.search("alpha", limit=5, use_fts=False)
    assert any(item["name"] == "alpha.txt" for item in like_results)
    alpha_entry = next(item for item in like_results if item["name"] == "alpha.txt")
    assert set(alpha_entry["tags"]) == {"reports", "work"}

    fts_results = index.search("beta", limit=5)
    assert any(item["name"] == "beta.txt" for item in fts_results)

    file_alpha.unlink()
    pruned = index.purge_missing([base])
    assert pruned == 1

    remaining = index.search("beta", limit=5, use_fts=False)
    assert {item["name"] for item in remaining} == {"beta.txt"}

    index.close()


def test_search_requires_query(tmp_path: Path) -> None:
    index = SQLiteIndex(tmp_path / "index.sqlite")
    with pytest.raises(ValueError):
        index.search("   ")
    index.close()
