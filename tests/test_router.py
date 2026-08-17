"""Tests for the router agent."""

import pytest

from app.errors import RoutingError, UpstreamError
from app.llm.client import RouteDecision
from app.router_agent import route_question


class FakeLLMClient:
    """Injectable fake that returns a preset decision or raises."""

    def __init__(self, decision: RouteDecision | None = None, raises=None):
        self._decision = decision
        self._raises = raises

    async def route(self, question: str) -> RouteDecision:
        if self._raises:
            raise self._raises
        return self._decision

    async def answer(self, question: str, context_blocks: list[str], history=None) -> str:
        return "fake answer"

    async def chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 200) -> str:
        return "fake chat answer"


@pytest.mark.asyncio
async def test_route_superhero():
    fake = FakeLLMClient(
        RouteDecision(route="superhero", superhero_names=["Spider-Man"], dataset_query="")
    )
    decision = await route_question("What are Spider-Man's powers?", client=fake)
    assert decision.route == "superhero"
    assert "Spider-Man" in decision.superhero_names


@pytest.mark.asyncio
async def test_route_dataset():
    fake = FakeLLMClient(
        RouteDecision(route="dataset", superhero_names=[], dataset_query="capital of Japan")
    )
    decision = await route_question("What is the capital of Japan?", client=fake)
    assert decision.route == "dataset"
    assert decision.dataset_query == "capital of Japan"


@pytest.mark.asyncio
async def test_route_both():
    fake = FakeLLMClient(
        RouteDecision(route="both", superhero_names=["Iron Man"], dataset_query="USA economy")
    )
    decision = await route_question("Is Iron Man from the USA?", client=fake)
    assert decision.route == "both"


@pytest.mark.asyncio
async def test_fallback_on_routing_error_hero_keyword():
    """When LLM raises RoutingError, keyword fallback detects hero name."""
    fake = FakeLLMClient(raises=RoutingError("parse error"))
    decision = await route_question("Tell me about batman", client=fake)
    assert decision.route == "superhero"
    assert any("batman" in n.lower() for n in decision.superhero_names)


@pytest.mark.asyncio
async def test_fallback_on_routing_error_no_hero():
    """When LLM raises RoutingError and no hero/country keyword, returns 'none'."""
    fake = FakeLLMClient(raises=RoutingError("parse error"))
    decision = await route_question("How do I make biryani?", client=fake)
    assert decision.route == "none"


@pytest.mark.asyncio
async def test_sanity_check_overrides_none_for_hero():
    """If LLM returns 'none' but question contains a hero keyword, override to 'superhero'."""
    fake = FakeLLMClient(
        RouteDecision(route="none", superhero_names=[], dataset_query="")
    )
    decision = await route_question("Tell me about spider-man", client=fake)
    assert decision.route == "superhero"


@pytest.mark.asyncio
async def test_sanity_check_overrides_none_for_country():
    """If LLM returns 'none' but question contains a country keyword, override to 'dataset'."""
    fake = FakeLLMClient(
        RouteDecision(route="none", superhero_names=[], dataset_query="")
    )
    decision = await route_question("What is the GDP of Japan?", client=fake)
    assert decision.route == "dataset"


@pytest.mark.asyncio
async def test_sanity_check_keeps_none_for_offtopic():
    """If LLM returns 'none' and no keyword matches, keep 'none'."""
    fake = FakeLLMClient(
        RouteDecision(route="none", superhero_names=[], dataset_query="")
    )
    decision = await route_question("How do I make biryani?", client=fake)
    assert decision.route == "none"


@pytest.mark.asyncio
async def test_upstream_error_propagates():
    """UpstreamError (LLM down) is NOT caught by fallback — should propagate."""
    fake = FakeLLMClient(raises=UpstreamError("groq", "500"))
    with pytest.raises(UpstreamError):
        await route_question("anything", client=fake)
