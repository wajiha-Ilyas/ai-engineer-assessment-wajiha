import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import (
    RoutingError,
    UpstreamError,
    UpstreamTimeout,
    routing_error_handler,
    upstream_error_handler,
    upstream_timeout_handler,
)
from app.llm.client import llm_client
from app.router_agent import route_question
from app.schemas import AskRequest, AskResponse
from app.synthesizer import synthesize
from app.tools.dataset import retriever
from app.tools.superhero import search_superhero

logging.basicConfig(level=settings.app_log_level.upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chatbot", version="0.1.0")

# CORS
origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

# Exception handlers
app.add_exception_handler(UpstreamError, upstream_error_handler)
app.add_exception_handler(UpstreamTimeout, upstream_timeout_handler)
app.add_exception_handler(RoutingError, routing_error_handler)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    question = body.question.strip()

    # 1. Route
    decision = await route_question(question, client=llm_client)

    # 2. Fetch context in parallel where applicable
    if decision.route in ("superhero", "both") and decision.superhero_names:
        hero_results_raw = await asyncio.gather(
            *[search_superhero(name) for name in decision.superhero_names],
            return_exceptions=False,
        )
        heroes = [h for h in hero_results_raw if h is not None]
    else:
        heroes = []

    if decision.route in ("dataset", "both"):
        query = decision.dataset_query or question
        dataset_chunks = retriever.retrieve(query, k=3)
    else:
        dataset_chunks = []

    # 3. Synthesize
    return await synthesize(question, decision, heroes, dataset_chunks, client=llm_client)
