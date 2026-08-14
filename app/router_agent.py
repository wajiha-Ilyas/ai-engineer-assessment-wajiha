"""Router agent — wraps the LLM client's route() with a keyword fallback."""

from __future__ import annotations

import re
import logging

from app.errors import RoutingError
from app.llm.client import LLMClientProtocol, RouteDecision, llm_client

logger = logging.getLogger(__name__)

# Small set of well-known hero/villain names for keyword fallback
_HERO_KEYWORDS = {
    "spider-man", "spiderman", "batman", "superman", "iron man", "ironman",
    "captain america", "thor", "hulk", "black widow", "wonder woman",
    "aquaman", "flash", "green lantern", "wolverine", "deadpool", "thanos",
    "joker", "loki", "hawkeye", "ant-man", "black panther", "doctor strange",
    "scarlet witch", "vision", "war machine", "falcon", "daredevil",
}


def _keyword_fallback(question: str) -> RouteDecision:
    """Best-effort routing using keyword matching when the LLM fails."""
    lower = question.lower()
    found = [name for name in _HERO_KEYWORDS if name in lower]
    if found:
        # Capitalise for the API query
        names = [n.title() for n in found]
        return RouteDecision(route="superhero", superhero_names=names, dataset_query="")
    return RouteDecision(route="dataset", superhero_names=[], dataset_query=question)


async def route_question(
    question: str,
    client: LLMClientProtocol | None = None,
) -> RouteDecision:
    """
    Route the question using the LLM. Falls back to keyword heuristics
    if the LLM raises RoutingError.
    """
    c = client or llm_client
    try:
        decision = await c.route(question)
        logger.info("LLM route=%s heroes=%s", decision.route, decision.superhero_names)
        return decision
    except RoutingError:
        logger.warning("Routing LLM failed; using keyword fallback")
        return _keyword_fallback(question)
