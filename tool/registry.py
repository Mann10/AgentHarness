from __future__ import annotations

import logging

from tool.config import MCPConfig
from tool.mcp_provider import MCPToolProvider
from tool.models import Tool, ToolProvider, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ToolProvider] = {}
        self._tool_map: dict[str, str] = {}
        self._provider_tools: dict[str, list[Tool]] = {}
        self._namespace_map: dict[str, str | None] = {}

    async def load_config(self, path: str) -> None:
        try:
            config = MCPConfig.from_file(path)
        except FileNotFoundError:
            logger.warning("MCP config file '%s' not found — no tools loaded", path)
            return
        except Exception as e:
            logger.error("Failed to load MCP config '%s': %s", path, e)
            return

        for server_cfg in config.servers:
            provider = MCPToolProvider(server_cfg)
            self._providers[server_cfg.name] = provider
            self._namespace_map[server_cfg.name] = server_cfg.namespace

    def add_provider(
        self, name: str, provider: ToolProvider, namespace: str | None = None
    ) -> list[Tool]:
        self._providers[name] = provider
        self._namespace_map[name] = namespace
        tools = list(self._provider_tools.get(name, []))
        return tools

    async def start(self) -> None:
        for name, provider in self._providers.items():
            try:
                await provider.start()
                tools = await provider.fetch_tools()
                self._register_tools(name, tools)
                tool_list = ", ".join(
                    f"{ns}_{t.name}" if (ns := self._namespace_map.get(name)) else t.name
                    for t in tools
                )
                logger.info(
                    "Provider '%s' registered %d tool(s): [%s]",
                    name, len(tools), tool_list,
                )
            except Exception as e:
                logger.error("Failed to start provider '%s': %s", name, e)

    async def shutdown(self) -> None:
        for name, provider in self._providers.items():
            try:
                await provider.shutdown()
            except Exception as e:
                logger.error("Error shutting down provider '%s': %s", name, e)
        self._providers.clear()
        self._tool_map.clear()
        self._provider_tools.clear()

    def add_provider_tools(self, provider_name: str, tools: list[Tool]) -> None:
        self._provider_tools[provider_name] = tools
        self._register_tools(provider_name, tools)

    def list_tools(self) -> list[Tool]:
        result = []
        for provider_name, tools in self._provider_tools.items():
            namespace = self._namespace_map.get(provider_name)
            for tool in tools:
                if namespace:
                    result.append(
                        Tool(
                            name=f"{namespace}_{tool.name}",
                            description=tool.description,
                            input_schema=tool.input_schema,
                        )
                    )
                else:
                    result.append(tool)
        return result

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        provider_name = self._tool_map.get(name)
        if provider_name is None:
            provider_name = self._resolve_with_namespace(name)

        if provider_name is None:
            raise ValueError(
                f"Unknown tool '{name}'. Available: {[t.name for t in self.list_tools()]}"
            )

        provider = self._providers[provider_name]
        namespace = self._namespace_map.get(provider_name)

        original_name = name
        if namespace:
            prefix = f"{namespace}_"
            if original_name.startswith(prefix):
                original_name = original_name[len(prefix) :]

        arg_summary = _summarize_args(arguments)
        logger.info(
            "TOOL CALL: %s (%s)  ──→  provider: '%s'",
            name, arg_summary, provider_name,
        )

        import time
        start = time.monotonic()
        result = await provider.call_tool(original_name, arguments)
        elapsed = time.monotonic() - start

        result_preview = result.content[:100].replace("\n", "\\n")
        if len(result.content) > 100:
            result_preview += "..."
        logger.info(
            "TOOL OK:   %s  ──→  done in %.2fs (len=%d): %s",
            name, elapsed, len(result.content), result_preview,
        )
        return result

    def _register_tools(self, provider_name: str, tools: list[Tool]) -> None:
        self._provider_tools[provider_name] = tools
        namespace = self._namespace_map.get(provider_name)

        for tool in tools:
            if namespace:
                llm_name = f"{namespace}_{tool.name}"
            else:
                llm_name = tool.name

            if llm_name in self._tool_map:
                existing = self._tool_map[llm_name]
                if existing != provider_name:
                    raise ValueError(
                        f"Tool name collision: '{llm_name}' already registered by "
                        f"provider '{existing}'. Add a 'namespace' to "
                        f"one of the servers in mcp_servers.json to disambiguate."
                    )

            self._tool_map[llm_name] = provider_name

    def _resolve_with_namespace(self, name: str) -> str | None:
        for provider_name, ns in self._namespace_map.items():
            if ns:
                prefix = f"{ns}_"
                if name.startswith(prefix):
                    return provider_name

        for provider_name, tools in self._provider_tools.items():
            ns = self._namespace_map.get(provider_name)
            if ns is None:
                for tool in tools:
                    if tool.name == name:
                        return provider_name

        return None

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    @property
    def tool_count(self) -> int:
        return len(self._tool_map)


def _summarize_args(arguments: dict) -> str:
    parts = []
    for k, v in arguments.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        if isinstance(v, str) and "\n" in v:
            s = s[:40] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts) if parts else "(no args)"
