"""Synthesizer — builds context blocks, calls LLM, assembles the final response."""

from __future__ import annotations

import logging

from app.llm.client import LLMClientProtocol, RouteDecision, llm_client
from app.schemas import AskResponse, Source
from app.tools.dataset import Chunk
from app.tools.fallback import handle_fallback
from app.tools.superhero import SuperheroResult

logger = logging.getLogger(__name__)


def _build_superhero_block(hero: SuperheroResult) -> str:
    return (
        f"Superhero: {hero.name}\n"
        f"Powerstats: {hero.powerstats}\n"
        f"Biography: {hero.biography}\n"
        f"Appearance: {hero.appearance}"
    )


def _build_dataset_block(chunk: Chunk) -> str:
    return f"[{chunk.title}] {chunk.text}"


async def synthesize(
    question: str,
    decision: RouteDecision,
    hero_results: list[SuperheroResult],
    dataset_chunks: list[Chunk],
    client: LLMClientProtocol | None = None,
) -> AskResponse:
    """
    Build context blocks from tool results, call the LLM to get a grounded
    answer, and assemble the final AskResponse with sources.
    """
    c = client or llm_client
    context_blocks: list[str] = []
    sources: list[Source] = []

    # Add superhero context blocks
    for hero in hero_results:
        context_blocks.append(_build_superhero_block(hero))
        sources.append(
            Source(
                kind="superhero_api",
                name=hero.name,
                url=hero.source_url,
            )
        )

    # Add dataset context blocks
    for chunk in dataset_chunks:
        context_blocks.append(_build_dataset_block(chunk))
        sources.append(
            Source(
                kind="dataset",
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                title=chunk.title,
            )
        )

    if not context_blocks:
        # No tool results — use the few-shot fallback (handles greetings,
        # self-intro, off-topic) instead of a static error string.
        answer = await handle_fallback(question, client=c)
    else:
        answer = await c.answer(question, context_blocks)

    return AskResponse(
        answer=answer,
        route=decision.route,
        sources=sources,
    )
