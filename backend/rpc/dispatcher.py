from __future__ import annotations

"""Request dispatcher — pure routing, no business logic.

Holds a mapping of method name -> handler callable.
The Dispatcher has no knowledge of RuntimeAPI or RPCAdapter.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from backend.rpc.protocol import (
    RPCRequest,
    RPCResponse,
    RPCError,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    INTERNAL_ERROR,
)

logger = logging.getLogger(__name__)


Handler = Callable[..., Awaitable[Any] | Any]


class Dispatcher:
    """Routes incoming JSON-RPC requests to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, method: str, handler: Handler) -> None:
        """Register a handler callable for a given method name."""
        self._handlers[method] = handler

    async def dispatch(self, request: RPCRequest) -> RPCResponse:
        """Look up the method in the registry and call the handler.

        Returns an RPCResponse with result or error.
        """
        handler = self._handlers.get(request.method)
        if handler is None:
            return RPCResponse(
                id=request.id,
                error=RPCError(
                    code=METHOD_NOT_FOUND,
                    message=f"Method not found: {request.method}",
                ),
            )

        # Basic params validation
        if request.params is not None and not isinstance(request.params, dict):
            return RPCResponse(
                id=request.id,
                error=RPCError(
                    code=INVALID_PARAMS,
                    message="Params must be a JSON object (dict) or null",
                ),
            )

        try:
            params: dict | None = request.params
            result = handler(params)
            if isinstance(result, Awaitable):
                result = await result
            return RPCResponse(
                id=request.id,
                result=result,
            )
        except RPCError as rpc_err:
            # Domain errors (D-08): return the handler's own code/message
            # verbatim — do NOT log (expected domain errors).
            return RPCResponse(
                id=request.id,
                error=rpc_err,
            )
        except Exception as exc:
            logger.exception("Handler error for method '%s': %s", request.method, exc)
            return RPCResponse(
                id=request.id,
                error=RPCError(
                    code=INTERNAL_ERROR,
                    message=f"Internal error: {exc}",
                ),
            )
