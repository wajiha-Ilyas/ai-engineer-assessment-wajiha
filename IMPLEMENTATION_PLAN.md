# Implementation Plan — AI Engineer Assessment

## 1. Requirements Recap

Build a FastAPI chatbot with a single endpoint `POST /ask` that:

- Accepts a natural language question and returns a response.
- Answers questions about **a text dataset of my choice** AND about **superheroes** (via the Superhero API).
- Routes intelligently: picks the right source, or both if the question spans both.
- Calls a **real hosted LLM** (Groq / Gemini / Cerebras / NVIDIA NIM) — no local models.
- Every response includes **where the information came from** (source attribution).
- Includes validations, sensible error handling, and tests covering core logic.
- Ships with a short README.

---

## 2. High-Level Architecture

```
                 ┌──────────────────────────┐
   POST /ask ──▶ │  FastAPI request layer   │
                 │  (validation, errors)    │
                 └───────────┬──────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │      Router / Planner    │  ← LLM classifies intent:
                 │  (LLM-based intent+slot) │    {superhero, dataset, both, none}
                 └───┬───────────────┬──────┘
                     │               │
        ┌────────────▼──┐        ┌───▼─────────────┐
        │ Superhero     │        │ Dataset         │
        │ tool          │        │ retriever (RAG) │
        │ (HTTP API)    │        │ (TF-IDF/BM25 +  │
        │               │        │  chunked docs)  │
        └────────┬──────┘        └────┬────────────┘
                 │                    │
                 └──────────┬─────────┘
                            ▼
                 ┌──────────────────────────┐
                 │  Answer synthesizer LLM  │  ← grounded prompt, cites sources
                 └───────────┬──────────────┘
                             ▼
                 ┌──────────────────────────┐
                 │  Response with `sources` │
                 └──────────────────────────┘
```

Two LLM calls per request in the general case (router + synthesizer). Kept
small so latency and cost stay reasonable; router uses a short prompt with
strict JSON output.

---

## 3. Tech Choices

| Concern           | Choice                                | Why                                                              |
| ----------------- | ------------------------------------- | ---------------------------------------------------------------- |
| Framework         | FastAPI + Uvicorn                     | Required by task; async, great validation via Pydantic.          |
| LLM provider      | **Groq** (Llama 3.x)                  | Free tier, very fast, JSON mode support for the router.          |
| HTTP client       | `httpx.AsyncClient`                   | Async, timeouts, retries, connection pooling.                    |
| Text dataset      | Small curated corpus (see §4)         | Keeps repo self-contained; no external DB required.              |
| Retrieval         | TF-IDF (scikit-learn) over chunks     | Zero-infra, deterministic, easy to test; upgrade path to embeds. |
| Config            | `pydantic-settings` + `.env`          | Standard, typed config, keeps secrets out of code.               |
| Tests             | `pytest` + `pytest-asyncio` + `respx` | Mock outbound HTTP (LLM + Superhero API) deterministically.      |
| Lint / format     | `ruff` + `ruff format`                | Single tool, fast.                                               |
| Python            | 3.11+                                 | Modern typing, `match`, good async.                              |

**Cuts / non-goals (intentional):**

- No vector DB / embeddings service — TF-IDF is enough for the demo corpus
  and testable offline.
- No auth on `/ask` — assessment scope.
- No persistent chat history — endpoint is stateless per the spec.
- No streaming responses — simpler contract, easier to test.

---

## 4. Text Dataset Choice

Use a small, self-contained corpus shipped in the repo under `data/`:
**Wikipedia-style plain-text articles about a narrow topic** (e.g., a handful
of countries, or a few tech companies). ~5–10 documents, each split into
paragraph-sized chunks. This:

- Makes routing meaningful (dataset vs. superhero is a real decision).
- Keeps the repo runnable with no external downloads.
- Gives the retriever enough material to demonstrate grounded answers.

Each chunk stored with metadata: `{doc_id, title, chunk_id, text, source_url}`.

---

## 5. Repository Layout

```
ai-engineer-assessment-wajiha/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, /ask, /health
│   ├── config.py               # Settings (env-driven)
│   ├── schemas.py              # Pydantic request/response models
│   ├── router_agent.py         # LLM-based intent classifier
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py           # Groq client wrapper (chat + JSON mode)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── superhero.py        # Superhero API client
│   │   └── dataset.py          # TF-IDF retriever over data/
│   ├── synthesizer.py          # Grounded answer prompt + citation assembly
│   └── errors.py               # Exception types + FastAPI handlers
├── data/
│   ├── index_meta.json         # Optional prebuilt chunk metadata
│   └── docs/*.txt              # Source documents
├── tests/
│   ├── conftest.py
│   ├── test_router.py
│   ├── test_superhero_tool.py
│   ├── test_dataset_tool.py
│   ├── test_synthesizer.py
│   └── test_ask_endpoint.py
├── .env.example
├── pyproject.toml              # deps + ruff + pytest config
├── README.md
└── IMPLEMENTATION_PLAN.md
```

---

## 6. API Contract

### `POST /ask`

Request:

```json
{ "question": "Who is Iron Man's alter ego and what country is he from?" }
```

Response (200):

```json
{
  "answer": "Iron Man's alter ego is Tony Stark. ...",
  "route": "both",
  "sources": [
    {
      "kind": "superhero_api",
      "name": "Iron Man",
      "url": "https://superheroapi.com/api/<redacted>/search/Iron%20Man"
    },
    {
      "kind": "dataset",
      "doc_id": "usa.txt",
      "chunk_id": 3,
      "title": "United States"
    }
  ]
}
```

Errors:

- `422` — invalid body (empty question, wrong types) via Pydantic.
- `502` — upstream failure (Superhero API or LLM) after retries.
- `504` — upstream timeout.
- `500` — unexpected; body: `{"detail": "internal error", "request_id": ...}`.

### `GET /health`

Cheap liveness check. Does not call upstreams.

---

## 7. Request Flow (detailed)

1. **Validate** input with Pydantic: non-empty, length-bounded (`1..1000` chars),
   stripped.
2. **Route** with LLM in JSON mode. Prompt asks for:
   ```json
   {
     "route": "superhero" | "dataset" | "both" | "none",
     "superhero_names": ["..."],   // if applicable
     "dataset_query": "..."         // rewritten query for retrieval
   }
   ```
   Fallback heuristic if LLM output is malformed: keyword scan for a small
   set of hero names + default to `dataset`.
3. **Fetch context** in parallel where possible (`asyncio.gather`):
   - `superhero`: call Superhero API for each name; keep top result’s
     `biography`, `powerstats`, `appearance`.
   - `dataset`: TF-IDF top-k (k=3) chunks for the rewritten query.
4. **Synthesize** with LLM: system prompt enforces "answer ONLY from the
   provided context; if insufficient, say so; cite sources by tag." Context
   blocks are prefixed with `[S1]`, `[S2]`, ... so the model can cite.
5. **Assemble response**: attach structured `sources` list (never trust
   model-emitted URLs).
6. **Return**.

---

## 8. Superhero API Integration

- Endpoint: `GET https://superheroapi.com/api/{token}/search/{name}`.
- Token from `SUPERHERO_API_TOKEN` env var; **never logged**, **never
  returned in response URLs** (redact token in `sources[].url`).
- `httpx.AsyncClient` with:
  - `timeout=10s` total, `connect=3s`.
  - 1 retry on network error / 5xx, exponential backoff.
- Response handling:
  - `response == "success"` → take `results[0]` (or all if disambiguation
    needed; keep simple: top match).
  - `response == "error"` → treat as "no data", not a 5xx. Synthesizer will
    say "no superhero data found for X."

---

## 9. Dataset Retriever

- On startup: load all `data/docs/*.txt`, split into ~500-char chunks with
  overlap, build TF-IDF matrix once, cache in memory.
- Query API: `retrieve(query: str, k: int = 3) -> list[Chunk]`.
- Deterministic → easy to unit test.
- Upgrade path documented in code comments: swap TF-IDF for embeddings +
  FAISS/Chroma without changing the tool interface.

---

## 10. LLM Client

- Single wrapper `LLMClient` with two methods:
  - `route(question) -> RouteDecision` (JSON mode, small model, temp 0).
  - `answer(question, context_blocks) -> str` (temp 0.2, max_tokens bounded).
- Reads `GROQ_API_KEY`, `GROQ_MODEL` from settings.
- Timeouts + 1 retry on transient errors.
- Injected via FastAPI dependency so tests can substitute a fake.

---

## 11. Error Handling & Validation

- Pydantic model `AskRequest(question: str = Field(min_length=1, max_length=1000))`.
- Custom exceptions: `UpstreamError`, `UpstreamTimeout`, `RoutingError`.
- Global exception handlers map them to the right HTTP status with a stable
  error shape.
- All outbound calls have explicit timeouts; no unbounded awaits.
- Request-scoped `request_id` (UUID) added to logs and error responses.
- Structured logging (JSON) with fields: `request_id`, `route`, `latency_ms`,
  `upstream`, `status`.

---

## 12. Security

- Secrets only via env (`.env` git-ignored; `.env.example` committed).
- Redact Superhero API token in any URL returned to clients.
- Input length capped; no shell / eval / dynamic imports on user input.
- CORS: allow-list configurable; default closed.
- No PII stored; endpoint is stateless.

---

## 13. Testing Strategy

Core logic tests (the parts the reviewer will care about):

1. **`test_router.py`** — router returns correct decision for
   representative questions; falls back gracefully on malformed LLM output.
   LLM is mocked.
2. **`test_superhero_tool.py`** — success path, `response=error` path,
   timeout path, token redaction in the returned source URL. `respx` mocks
   HTTP.
3. **`test_dataset_tool.py`** — retriever returns expected top chunk for a
   query with obvious lexical overlap; empty corpus behavior.
4. **`test_synthesizer.py`** — prompt includes all context blocks; when
   context is empty, model is instructed to say "insufficient info" (checked
   via mocked LLM being called with the right messages).
5. **`test_ask_endpoint.py`** — end-to-end with mocked LLM + mocked
   Superhero API:
   - happy path superhero-only,
   - happy path dataset-only,
   - `both` route merges sources,
   - `422` on empty question,
   - `502` when LLM upstream fails.

Run: `pytest -q`.

---

## 14. Configuration

`.env.example`:

```
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
SUPERHERO_API_TOKEN=
APP_LOG_LEVEL=INFO
ALLOWED_ORIGINS=
```

`app/config.py` uses `pydantic-settings` with typed fields and defaults.

---

## 15. Local Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in keys
uvicorn app.main:app --reload
```

Smoke test:

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question":"What are Iron Man's powerstats?"}' | jq
```

---

## 16. README Outline (kept short, per spec)

1. What it is (2–3 lines).
2. Setup: clone, venv, install, env vars.
3. Run: uvicorn command.
4. Example request + response.
5. Test command.
6. One paragraph on architecture with a link to `IMPLEMENTATION_PLAN.md`.

---

## 17. Build Order (execution checklist)

1. `pyproject.toml`, project skeleton, `.env.example`, `.gitignore` additions.
2. `config.py`, `schemas.py`, `errors.py`, `main.py` with `/health` and a stub `/ask`.
3. `tools/dataset.py` + sample docs + unit tests.
4. `tools/superhero.py` + unit tests with `respx`.
5. `llm/client.py` wrapper (Groq) with injectable interface.
6. `router_agent.py` + tests.
7. `synthesizer.py` + tests.
8. Wire everything into `/ask`; end-to-end tests.
9. Logging, error handlers, token redaction pass.
10. README + final polish + push to public repo `ai-engineer-assessment-wajiha`.

---

## 18. Known Trade-offs (things I will own in the interview)

- **TF-IDF over embeddings**: cheaper, deterministic, testable; may miss
  paraphrases. Acceptable for a small curated corpus.
- **Two LLM calls per request**: cleaner separation of concerns and more
  reliable citations vs. a single "tool-calling" prompt. Costs one extra
  round-trip; acceptable on Groq's latency.
- **Top-1 superhero match**: skipping disambiguation UX to keep scope tight;
  documented as future work.
- **No streaming**: simpler contract; easy to add later without breaking
  clients.
- **In-memory index built at startup**: fine for the demo corpus size; would
  move to a persisted index for larger data.
