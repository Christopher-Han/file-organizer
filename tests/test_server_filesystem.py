from pathlib import Path

from organizer.server import FileOrganizerServer, ServerContext, register_filesystem_tools


def build_context(tmp_path: Path) -> ServerContext:
    return ServerContext.from_base_dir(tmp_path / ".organizer")


def test_scan_index_and_search_tool(tmp_path: Path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)
    register_filesystem_tools(server)

    root_dir = tmp_path / "files"
    root_dir.mkdir()
    file_path = root_dir / "note.txt"
    file_path.write_text("hello world")

    scan_result = server.handle("scan_paths", {"paths": [str(root_dir)]})
    assert scan_result["stats"]["scanned"] == 1
    assert scan_result["errors"] == []

    index_result = server.handle("index_paths", {"paths": [str(root_dir)]})
    assert index_result["indexed"] == 1
    assert index_result["errors"] == []

    search_result = server.handle("search_files", {"query": "note", "use_fts": False})
    assert search_result["count"] == 1
    assert search_result["results"][0]["name"] == "note.txt"

    file_path.unlink()
    reindex_result = server.handle("index_paths", {"paths": [str(root_dir)], "prune": True})
    assert reindex_result["pruned"] == 1

    context.close()
