"""Groq LLM client wrapper.

Two methods:
  - route(question) -> RouteDecision   (JSON mode, temp=0, small prompt)
  - answer(question, context_blocks)  -> str  (grounded synthesis, temp=0.2)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Literal, Protocol

from groq import AsyncGroq, APITimeoutError, APIError

from app.config import settings
from app.errors import UpstreamError, UpstreamTimeout, RoutingError

logger = logging.getLogger(__name__)

RouteLabel = Literal["superhero", "dataset", "both", "none"]


@dataclass
class RouteDecision:
    route: RouteLabel
    superhero_names: list[str] = field(default_factory=list)
    dataset_query: str = ""


# ---------------------------------------------------------------------------
# Protocol — lets tests inject a fake without subclassing
# ---------------------------------------------------------------------------

class LLMClientProtocol(Protocol):
    async def route(self, question: str) -> RouteDecision: ...
    async def answer(
        self,
        question: str,
        context_blocks: list[str],
        history: list[dict] | None = None,
    ) -> str: ...
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.4,
        max_tokens: int = 200,
    ) -> str: ...


# ---------------------------------------------------------------------------
# Real implementation
# ---------------------------------------------------------------------------

_ROUTER_SYSTEM = """\
You are a question router. Classify the user question and respond ONLY with valid JSON.

Rules:
- "superhero": question is about a fictional superhero or supervillain character (Marvel, DC, etc.)
- "dataset": question is about countries, geography, history, economy, culture, or sports.
- "both": question involves BOTH a superhero AND a country/world topic.
- "none": greeting, small talk, off-topic (food, math, weather, etc.), or unclear.

Output schema (no markdown, no extra keys):
{"route": "...", "superhero_names": [...], "dataset_query": "..."}

Examples:
Q: Who is Batman?
A: {"route": "superhero", "superhero_names": ["Batman"], "dataset_query": ""}

Q: What are Spider-Man's powers?
A: {"route": "superhero", "superhero_names": ["Spider-Man"], "dataset_query": ""}

Q: Iron Man powerstats
A: {"route": "superhero", "superhero_names": ["Iron Man"], "dataset_query": ""}

Q: Tell me about Japan's economy
A: {"route": "dataset", "superhero_names": [], "dataset_query": "Japan economy GDP"}

Q: What is Germany's capital?
A: {"route": "dataset", "superhero_names": [], "dataset_query": "Germany capital city"}

Q: Population of Brazil
A: {"route": "dataset", "superhero_names": [], "dataset_query": "Brazil population"}

Q: Is Iron Man from the USA?
A: {"route": "both", "superhero_names": ["Iron Man"], "dataset_query": "USA country facts"}

Q: Hi there
A: {"route": "none", "superhero_names": [], "dataset_query": ""}

Q: How do I make biryani?
A: {"route": "none", "superhero_names": [], "dataset_query": ""}

Q: What is 2+2?
A: {"route": "none", "superhero_names": [], "dataset_query": ""}
"""

_ANSWER_SYSTEM = """\
You are a helpful assistant. Answer the user's question using ONLY the context blocks provided.
Each block is tagged [S1], [S2], etc. Cite the tag(s) you used at the end of your answer in parentheses.
If the context is insufficient, say so honestly. Do not make up information.
"""


class LLMClient:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def route(self, question: str) -> RouteDecision:
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _ROUTER_SYSTEM},
                    {"role": "user", "content": question},
                ],
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
        except APITimeoutError as exc:
            raise UpstreamTimeout("groq") from exc
        except APIError as exc:
            raise UpstreamError("groq", str(exc)) from exc

        raw = completion.choices[0].message.content or ""
        try:
            data = json.loads(raw)
            return RouteDecision(
                route=data.get("route", "none"),
                superhero_names=data.get("superhero_names") or [],
                dataset_query=data.get("dataset_query") or question,
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Router returned unparseable JSON: %r", raw)
            raise RoutingError(f"Router JSON parse failed: {exc}") from exc

    async def answer(
        self,
        question: str,
        context_blocks: list[str],
        history: list[dict] | None = None,
    ) -> str:
        context_text = "\n\n".join(
            f"[S{i + 1}] {block}" for i, block in enumerate(context_blocks)
        )
        user_msg = f"Context:\n{context_text}\n\nQuestion: {question}"

        messages: list[dict] = [{"role": "system", "content": _ANSWER_SYSTEM}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_msg})

        return await self.chat(messages, temperature=0.2, max_tokens=512)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.4,
        max_tokens: int = 200,
    ) -> str:
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except APITimeoutError as exc:
            raise UpstreamTimeout("groq") from exc
        except APIError as exc:
            raise UpstreamError("groq", str(exc)) from exc

        return completion.choices[0].message.content or ""


# Module-level singleton
llm_client: LLMClientProtocol = LLMClient()
