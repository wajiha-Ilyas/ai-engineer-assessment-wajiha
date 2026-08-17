"""Router agent — wraps the LLM client's route() with a keyword fallback."""

from __future__ import annotations

import logging

from app.errors import RoutingError
from app.llm.client import LLMClientProtocol, RouteDecision, llm_client

logger = logging.getLogger(__name__)

# Known hero/villain keywords for local override
_HERO_KEYWORDS = {
    "spider-man", "spiderman", "batman", "superman", "iron man", "ironman",
    "captain america", "thor", "hulk", "black widow", "wonder woman",
    "aquaman", "flash", "green lantern", "wolverine", "deadpool", "thanos",
    "joker", "loki", "hawkeye", "ant-man", "black panther", "doctor strange",
    "scarlet witch", "vision", "war machine", "falcon", "daredevil",
    "captain marvel", "groot", "star-lord", "gamora", "rocket", "nebula",
    "cyborg", "nightwing", "robin", "batgirl", "supergirl", "shazam",
}

# Country / geography keywords for local override
_COUNTRY_KEYWORDS = {
    "usa", "united states", "america", "american",
    "japan", "japanese", "tokyo",
    "germany", "german", "berlin",
    "brazil", "brazilian", "sao paulo", "amazon",
    "australia", "australian", "sydney", "canberra",
}


def _keyword_fallback(question: str) -> RouteDecision:
    """Best-effort routing using keyword matching when the LLM fails or returns 'none'."""
    lower = question.lower()
    heroes = [name for name in _HERO_KEYWORDS if name in lower]
    countries = [kw for kw in _COUNTRY_KEYWORDS if kw in lower]

    if heroes and countries:
        return RouteDecision(
            route="both",
            superhero_names=[n.title() for n in heroes],
            dataset_query=question,
        )
    if heroes:
        return RouteDecision(
            route="superhero",
            superhero_names=[n.title() for n in heroes],
            dataset_query="",
        )
    if countries:
        return RouteDecision(route="dataset", superhero_names=[], dataset_query=question)

    return RouteDecision(route="none", superhero_names=[], dataset_query="")


def _sanity_check(decision: RouteDecision, question: str) -> RouteDecision:
    """
    If the LLM returned 'none' but keywords clearly indicate superhero or country,
    override the decision. This protects against the LLM misclassifying obvious queries.
    """
    if decision.route != "none":
        return decision

    override = _keyword_fallback(question)
    if override.route != "none":
        logger.info(
            "Router returned 'none' but keyword check found route=%s — overriding",
            override.route,
        )
        return override

    return decision


async def route_question(
    question: str,
    client: LLMClientProtocol | None = None,
) -> RouteDecision:
    """
    Route the question using the LLM, with keyword sanity-check and fallback.
    """
    c = client or llm_client
    try:
        decision = await c.route(question)
        decision = _sanity_check(decision, question)
        logger.info("route=%s heroes=%s", decision.route, decision.superhero_names)
        return decision
    except RoutingError:
        logger.warning("Routing LLM failed; using keyword fallback")
        return _keyword_fallback(question)
