"""MCP server package for the Agentic File Organizer."""

from .app import FileOrganizerServer, ToolExecutionError, ToolRouter, UnknownToolError
from .context import ServerContext
from .filesystem import register_filesystem_tools
from .memory import register_memory_tools
from .rules import register_rule_tools

__all__ = [
    "FileOrganizerServer",
    "ToolExecutionError",
    "ToolRouter",
    "UnknownToolError",
    "ServerContext",
    "register_filesystem_tools",
    "register_memory_tools",
    "register_rule_tools",
]
