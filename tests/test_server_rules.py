from pathlib import Path

from organizer.server import FileOrganizerServer, ServerContext, register_rule_tools


def build_context(tmp_path: Path) -> ServerContext:
    return ServerContext.from_base_dir(tmp_path / ".organizer")


def seed_rule(context: ServerContext, destination: Path) -> None:
    payload = context.memory_store.load()
    payload.setdefault("rules", []).append(
        {
            "name": "Move text",
            "definition": {
                "when": [{"extension": "txt"}],
                "actions": [
                    {
                        "type": "move",
                        "destination": str(destination),
                    }
                ],
            },
        }
    )
    context.memory_store.save(payload)


def test_suggest_stage_apply_and_rollback(tmp_path: Path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)
    register_rule_tools(server)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    destination = tmp_path / "archive"
    destination.mkdir()

    seed_rule(context, destination)

    source_file = inbox / "notes.txt"
    source_file.write_text("hello")

    suggest_payload = {
        "files": [
            {
                "path": str(source_file),
                "extension": "txt",
                "size": 5,
            }
        ]
    }

    suggest_result = server.handle("suggest_organization", suggest_payload)
    assert suggest_result["count"] == 1
    suggestion = suggest_result["suggestions"][0]
    assert suggestion["destination"].startswith(str(destination))

    stage_result = server.handle("stage_changes", {"suggestions": [suggestion]})
    manifest_id = stage_result["manifest_id"]
    staged_entries = stage_result["entries"]
    assert len(staged_entries) == 1
    staged_path = Path(stage_result["path"])
    assert staged_path.exists()

    preview = server.handle("preview_diff", {"manifest_id": manifest_id})
    assert "MOVE" in preview["preview"]

    apply_result = server.handle("apply_manifest", {"manifest_id": manifest_id})
    log_path = Path(apply_result["log_path"])
    assert log_path.exists()
    assert (destination / "notes.txt").exists()
    assert not source_file.exists()

    server.handle("rollback_manifest", {"manifest_id": manifest_id})
    assert source_file.exists()
    assert not (destination / "notes.txt").exists()

    context.close()


def test_inline_rule_override(tmp_path: Path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)
    register_rule_tools(server)

    source_file = tmp_path / "report.pdf"
    source_file.write_text("data")
    target_dir = tmp_path / "reports"
    target_dir.mkdir()

    suggest_result = server.handle(
        "suggest_organization",
        {
            "files": [
                {
                    "path": str(source_file),
                    "extension": "pdf",
                }
            ],
            "rules": {
                "Move PDF": {
                    "when": [{"extension": "pdf"}],
                    "actions": [
                        {
                            "type": "move",
                            "destination": str(target_dir),
                        }
                    ],
                }
            },
        },
    )

    assert suggest_result["count"] == 1
    assert suggest_result["suggestions"][0]["destination"].startswith(str(target_dir))

    context.close()
