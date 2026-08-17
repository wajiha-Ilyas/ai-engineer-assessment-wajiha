import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

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
from app.logging_config import configure_logging
from app.memory import ConversationStore, InMemoryStore, create_store
from app.router_agent import route_question
from app.schemas import AskRequest, AskResponse
from app.synthesizer import synthesize
from app.tools.dataset import retriever
from app.tools.superhero import search_superhero

configure_logging(settings.app_log_level)
logger = logging.getLogger(__name__)

# Module-level fallback store used when lifespan hasn't run (e.g. tests)
_default_store: ConversationStore = InMemoryStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    store = await create_store(settings.redis_url, settings.session_ttl_seconds)
    app.state.store = store
    logger.info("Startup complete")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    await app.state.store.close()
    logger.info("Shutdown complete")


app = FastAPI(title="AI Chatbot — Nova", version="0.1.0", lifespan=lifespan)

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
        "HTTP %s %s -> %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        extra={"request_id": request_id, "latency_ms": latency_ms},
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
async def health(request: Request) -> dict:
    store = getattr(request.app.state, "store", _default_store)
    memory_ok = await store.ping()
    return {"status": "ok", "memory_backend": type(store).__name__, "memory_ok": memory_ok}


@app.post("/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest) -> AskResponse:
    store: ConversationStore = getattr(request.app.state, "store", _default_store)
    question = body.question.strip()

    # Resolve or generate session_id
    session_id = body.session_id or str(uuid.uuid4())

    # 1. Load conversation history
    history = await store.get(session_id)

    # 2. Route
    decision = await route_question(question, client=llm_client)

    # 3. Fetch context in parallel
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

    # 4. Synthesize
    response = await synthesize(
        question,
        decision,
        heroes,
        dataset_chunks,
        client=llm_client,
        history=history,
        session_id=session_id,
    )

    # 5. Persist the new turn
    await store.append(session_id, question, response.answer)

    return response
