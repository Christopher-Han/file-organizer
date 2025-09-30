"""Scaffolding for the MCP file organizer server."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, MutableMapping, Protocol

from .context import ServerContext


class ToolHandler(Protocol):
    def __call__(self, payload: MutableMapping[str, Any], context: ServerContext) -> Any:  # pragma: no cover - protocol
        ...


class UnknownToolError(KeyError):
    """Raised when a request targets an unregistered tool."""


class ToolExecutionError(RuntimeError):
    """Wrap errors raised by tool handlers with context."""

    def __init__(self, tool_name: str, original: Exception) -> None:
        super().__init__(f"Tool '{tool_name}' failed: {original}")
        self.tool_name = tool_name
        self.original = original


@dataclass
class ToolRouter:
    """Registry of MCP tool handlers."""

    handlers: Dict[str, ToolHandler] = field(default_factory=dict)

    def register(self, name: str, handler: ToolHandler) -> None:
        if name in self.handlers:
            raise ValueError(f"Tool '{name}' is already registered")
        self.handlers[name] = handler

    def dispatch(self, name: str, payload: MutableMapping[str, Any], context: ServerContext) -> Any:
        if name not in self.handlers:
            raise UnknownToolError(name)

        handler = self.handlers[name]
        try:
            return handler(payload, context)
        except UnknownToolError:
            raise
        except Exception as exc:  # pragma: no cover - ensures context propagation
            raise ToolExecutionError(name, exc) from exc


@dataclass
class FileOrganizerServer:
    """Minimal server orchestrator for registering and invoking MCP tools."""

    context: ServerContext
    router: ToolRouter = field(default_factory=ToolRouter)

    def tool(self, name: str) -> Callable[[ToolHandler], ToolHandler]:
        """Decorator for registering a tool handler."""

        def decorator(handler: ToolHandler) -> ToolHandler:
            self.router.register(name, handler)
            return handler

        return decorator

    def handle(self, name: str, payload: MutableMapping[str, Any]) -> Any:
        """Invoke the handler registered for ``name``."""

        return self.router.dispatch(name, payload, self.context)


__all__ = [
    "FileOrganizerServer",
    "ToolRouter",
    "ToolExecutionError",
    "UnknownToolError",
]
