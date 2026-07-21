from __future__ import annotations

import logging
import os
from collections.abc import Callable

from tool.models import Tool, ToolResult

logger = logging.getLogger(__name__)


class LocalToolProvider:
    def __init__(self) -> None:
        self._tools: list[Tool] = []
        self._handlers: dict[str, Callable[[dict], str]] = {}

    def add_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable[[dict], str],
    ) -> None:
        self._tools.append(
            Tool(name=name, description=description, input_schema=input_schema)
        )
        self._handlers[name] = handler

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def fetch_tools(self) -> list[Tool]:
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown local tool '{name}'")
        logger.debug("Local tool '%s' called with args=%s", name, arguments)
        try:
            result = handler(arguments)
            return ToolResult(tool_call_id=name, content=str(result))
        except Exception as e:
            logger.error("Local tool '%s' failed: %s", name, e)
            return ToolResult(tool_call_id=name, content=f"Error: {e}")


# --- Built-in tool handlers ---


def _read_file(args: dict) -> str:
    path = args.get("path", "")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _write_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} bytes to {path}"


def _list_dir(args: dict) -> str:
    path = args.get("path", ".")
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Directory not found: {path}")
    entries = os.listdir(path)
    lines = []
    for name in sorted(entries):
        full = os.path.join(path, name)
        if os.path.isdir(full):
            lines.append(f"{name}/")
        else:
            size = os.path.getsize(full)
            lines.append(f"{name}  ({size} bytes)")
    return "\n".join(lines)


def register_builtin_tools(provider: LocalToolProvider) -> None:
    provider.add_tool(
        name="read_file",
        description="Read the contents of a file on the local filesystem.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file",
                }
            },
            "required": ["path"],
        },
        handler=_read_file,
    )

    provider.add_tool(
        name="write_file",
        description="Write content to a file on the local filesystem. Creates parent directories if needed.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        handler=_write_file,
    )

    provider.add_tool(
        name="list_dir",
        description="List files and directories in a directory on the local filesystem.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the directory",
                }
            },
            "required": ["path"],
        },
        handler=_list_dir,
    )
