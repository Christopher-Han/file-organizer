from pathlib import Path

from organizer.server import FileOrganizerServer, ServerContext, register_memory_tools


def build_context(tmp_path: Path) -> ServerContext:
    return ServerContext.from_base_dir(tmp_path / ".organizer")


def test_get_and_update_memory(tmp_path: Path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)
    register_memory_tools(server)

    result = server.handle("get_memory", {})
    assert result["memory"]["rules"] == []

    update = {
        "patch": {"preferences": {"tone": "concise"}},
    }
    updated = server.handle("update_memory", update)
    assert updated["memory"]["preferences"]["tone"] == "concise"

    context.close()


def test_learn_from_confirmations(tmp_path: Path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)
    register_memory_tools(server)

    payload = {
        "confirmations": [
            {"rule_name": "Move text", "accepted": True},
            {"rule_name": "Move text", "accepted": False},
        ]
    }
    result = server.handle("learn_from_confirmations", payload)
    stats = result["memory"]["preferences"]["confirmation_stats"]["Move text"]
    assert stats["accepted"] == 1
    assert stats["rejected"] == 1

    context.close()
