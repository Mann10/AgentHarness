from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from tool.config import MCPServerConfig
from tool.models import Tool, ToolResult

logger = logging.getLogger(__name__)


class MCPToolProvider:
    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._session: ClientSession | None = None
        self._transport_cm = None

    async def start(self) -> None:
        if self._config.command:
            await self._start_stdio()
        elif self._config.url:
            await self._start_http()
        else:
            raise ValueError(
                f"MCP server '{self._config.name}' has neither 'command' nor 'url'"
            )

    async def _start_stdio(self) -> None:
        params = StdioServerParameters(
            command=self._config.command,
            args=self._config.args or [],
            env=self._config.env,
        )
        self._transport_cm = stdio_client(params)
        streams = await self._transport_cm.__aenter__()
        read, write = streams
        self._session = await ClientSession(read, write).__aenter__()
        await self._session.initialize()
        logger.info(
            "MCP stdio server '%s' started (cmd: %s)", self._config.name, self._config.command
        )

    async def _start_http(self) -> None:
        headers = self._config.headers or {}
        self._transport_cm = streamable_http_client(self._config.url, headers=headers)

        try:
            streams = await self._transport_cm.__aenter__()
        except Exception as e:
            logger.error(
                "MCP HTTP server '%s' failed to connect to %s: %s",
                self._config.name,
                self._config.url,
                e,
            )
            raise

        read, write, _ = streams
        self._session = await ClientSession(read, write).__aenter__()
        await self._session.initialize()
        logger.info(
            "MCP HTTP server '%s' connected to %s", self._config.name, self._config.url
        )

    async def shutdown(self) -> None:
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._transport_cm:
            await self._transport_cm.__aexit__(None, None, None)
            self._transport_cm = None
        logger.info("MCP server '%s' shut down", self._config.name)

    async def fetch_tools(self) -> list[Tool]:
        if not self._session:
            raise RuntimeError(f"MCP server '{self._config.name}' is not started")
        response = await self._session.list_tools()
        return [
            Tool(
                name=t.name,
                description=t.description or "",
                input_schema=t.inputSchema or {},
            )
            for t in response.tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        if not self._session:
            raise RuntimeError(f"MCP server '{self._config.name}' is not started")
        logger.debug(
            "MCP call_tool '%s/%s' args=%s", self._config.name, name, arguments
        )
        result = await self._session.call_tool(name, arguments=arguments)

        if result.isError:
            error_text = ""
            for c in result.content:
                if isinstance(c, TextContent):
                    error_text += c.text
            logger.warning(
                "MCP tool '%s/%s' returned error: %s",
                self._config.name, name, error_text[:200],
            )

        parts = []
        for content in result.content:
            if isinstance(content, TextContent):
                parts.append(content.text)

        text = "\n".join(parts)
        return ToolResult(tool_call_id=name, content=text)
