# LLM Client Module Refactor

## Goal
Replace flat `llm.py` with a `llm/` package centered around an extensible `BaseLLMClient` ABC.

## Files to Create

| File | Contents |
|---|---|
| `llm/__init__.py` | Exports `BaseLLMClient`, `OpenAIClient`, `LLMError`, `LLMConnectionError`, `LLMResponseError` |
| `llm/base.py` | `BaseLLMClient` ABC with `chat()` and `stream_chat()` abstract methods, `count_tokens()` default |
| `llm/openai_client.py` | `OpenAIClient(BaseLLMClient)` wrapping `openai.OpenAI` SDK |
| `llm/errors.py` | `LLMError` → `LLMConnectionError`, `LLMResponseError` |

## Files to Modify

| File | Changes |
|---|---|
| `config.py` | Add `temperature: float` (default 0.7) and `max_tokens: int` (default 4096) fields |
| `main.py` | Use `OpenAIClient(config)` instead of `ask_llm()` |
| `requirements.txt` | Add `tiktoken>=0.7.0` |

## Files to Delete

| File | Reason |
|---|---|
| `llm.py` | Replaced by `llm/` package |

## Design Details

### BaseLLMClient (base.py)
- `__init__(self, config: Config)` — stores config
- `chat(self, messages: list[dict], **kwargs) -> str` — abstract
- `stream_chat(self, messages: list[dict], **kwargs) -> Generator[str, None, None]` — abstract, placeholder for later
- `count_tokens(self, text: str) -> int` — optional override; uses tiktoken if available, falls back to estimation

### OpenAIClient (openai_client.py)
- Constructor accepts `Config`, creates `openai.OpenAI` client
- `chat()` merges `**kwargs` (temperature, max_tokens) over Config defaults
- Wraps SDK calls in try/except: `APIConnectionError` → `LLMConnectionError`, others → `LLMResponseError`

### Error Hierarchy (errors.py)
```
LLMError(Exception)
├── LLMConnectionError     # connection/auth failures
└── LLMResponseError       # unexpected response, API errors
```

### Config additions (config.py)
- `temperature: float` — env var `TEMPERATURE`, default `0.7`
- `max_tokens: int` — env var `MAX_TOKENS`, default `4096`
