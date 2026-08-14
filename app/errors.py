from fastapi import Request
from fastapi.responses import JSONResponse


class UpstreamError(Exception):
    """Non-timeout failure calling an upstream service."""
    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        super().__init__(f"{service}: {detail}")


class UpstreamTimeout(Exception):
    """Upstream service timed out."""
    def __init__(self, service: str):
        self.service = service
        super().__init__(f"{service} timed out")


class RoutingError(Exception):
    """LLM router returned an unparseable response."""


async def upstream_error_handler(request: Request, exc: UpstreamError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": f"Upstream error from {exc.service}", "message": exc.detail},
    )


async def upstream_timeout_handler(request: Request, exc: UpstreamTimeout) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={"detail": f"Upstream timeout from {exc.service}"},
    )


async def routing_error_handler(request: Request, exc: RoutingError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "Router failed to classify the question"},
    )
