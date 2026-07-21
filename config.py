from dataclasses import dataclass, field
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    base_url: str = field(default_factory=lambda: getenv("OPENAI_BASE_URL", "http://localhost:20128/v1"))
    model: str = field(default_factory=lambda: getenv("OPENAI_MODEL", "free-stack"))
    api_key: str = field(default_factory=lambda: getenv("OPENAI_API_KEY", ""))
    system_prompt: str = field(default_factory=lambda: getenv("SYSTEM_PROMPT", "You are a helpful assistant."))
    temperature: float = field(default_factory=lambda: float(getenv("TEMPERATURE", "0.7")))
    max_tokens: int = field(default_factory=lambda: int(getenv("MAX_TOKENS", "4096")))
    mcp_config_path: str = field(default_factory=lambda: getenv("MCP_CONFIG_PATH", "mcp_servers.json"))
