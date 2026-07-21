from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    name: str
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    namespace: str | None = None


@dataclass
class MCPConfig:
    servers: list[MCPServerConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "MCPConfig":
        raw_servers = data.get("mcpServers", [])
        servers = [MCPServerConfig(**s) for s in raw_servers]
        return cls(servers=servers)

    @classmethod
    def from_file(cls, path: str) -> "MCPConfig":
        import json

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
