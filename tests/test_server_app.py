from collections.abc import MutableMapping
from typing import Any

import pytest

from organizer.server import (
    FileOrganizerServer,
    ServerContext,
    ToolExecutionError,
    UnknownToolError,
)
def build_context(tmp_path) -> ServerContext:
    return ServerContext.from_base_dir(tmp_path / ".organizer")


def test_tool_registration_and_dispatch(tmp_path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)

    @server.tool("ping")
    def _ping(payload: MutableMapping[str, Any], ctx: ServerContext) -> dict[str, Any]:
        ctx.index.connect()
        return {"echo": payload["value"], "root": str(ctx.paths.root)}

    result = server.handle("ping", {"value": "hello"})
    assert result["echo"] == "hello"
    assert result["root"].endswith(".organizer")

    context.close()


def test_unknown_tool(tmp_path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)

    with pytest.raises(UnknownToolError):
        server.handle("missing", {})

    context.close()


def test_handler_error_wrapped(tmp_path) -> None:
    context = build_context(tmp_path)
    server = FileOrganizerServer(context)

    @server.tool("explode")
    def _explode(payload: MutableMapping[str, Any], ctx: ServerContext) -> None:
        raise ValueError("boom")

    with pytest.raises(ToolExecutionError) as exc:
        server.handle("explode", {})

    assert exc.value.tool_name == "explode"
    assert isinstance(exc.value.original, ValueError)

    context.close()
