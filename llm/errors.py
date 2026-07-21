class LLMError(Exception):
    pass


class LLMConnectionError(LLMError):
    pass


class LLMResponseError(LLMError):
    pass
