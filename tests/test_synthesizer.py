"""Tests for the synthesizer."""

import pytest

from app.llm.client import RouteDecision
from app.schemas import AskResponse
from app.synthesizer import synthesize
from app.tools.dataset import Chunk
from app.tools.superhero import SuperheroResult


class FakeLLMClient:
    def __init__(self, answer_text: str = "Fake synthesized answer [S1]"):
        self.last_context_blocks: list[str] = []
        self._answer_text = answer_text

    async def route(self, question: str) -> RouteDecision:
        return RouteDecision(route="none")

    async def answer(self, question: str, context_blocks: list[str]) -> str:
        self.last_context_blocks = context_blocks
        return self._answer_text


HERO = SuperheroResult(
    name="Iron Man",
    powerstats={"strength": "85"},
    biography={"full-name": "Tony Stark"},
    appearance={"gender": "Male"},
    source_url="https://superheroapi.com/api/REDACTED/search/Iron+Man",
)

CHUNK = Chunk(doc_id="usa", chunk_id=0, title="United States of America", text="The USA is a federal republic.")


@pytest.mark.asyncio
async def test_synthesize_superhero_only():
    fake = FakeLLMClient()
    decision = RouteDecision(route="superhero", superhero_names=["Iron Man"])
    resp = await synthesize("Who is Iron Man?", decision, [HERO], [], client=fake)

    assert isinstance(resp, AskResponse)
    assert resp.route == "superhero"
    assert len(resp.sources) == 1
    assert resp.sources[0].kind == "superhero_api"
    assert resp.sources[0].name == "Iron Man"
    # LLM was called with one context block containing the hero data
    assert len(fake.last_context_blocks) == 1
    assert "Iron Man" in fake.last_context_blocks[0]


@pytest.mark.asyncio
async def test_synthesize_dataset_only():
    fake = FakeLLMClient()
    decision = RouteDecision(route="dataset", dataset_query="federal republic")
    resp = await synthesize("Is the USA a republic?", decision, [], [CHUNK], client=fake)

    assert resp.route == "dataset"
    assert len(resp.sources) == 1
    assert resp.sources[0].kind == "dataset"
    assert resp.sources[0].doc_id == "usa"


@pytest.mark.asyncio
async def test_synthesize_both():
    fake = FakeLLMClient()
    decision = RouteDecision(route="both", superhero_names=["Iron Man"], dataset_query="USA")
    resp = await synthesize("Is Iron Man from the USA?", decision, [HERO], [CHUNK], client=fake)

    assert resp.route == "both"
    assert len(resp.sources) == 2
    assert {s.kind for s in resp.sources} == {"superhero_api", "dataset"}
    assert len(fake.last_context_blocks) == 2


@pytest.mark.asyncio
async def test_synthesize_no_context_skips_llm():
    """When there are no context blocks, LLM should NOT be called."""
    fake = FakeLLMClient()
    decision = RouteDecision(route="none")
    resp = await synthesize("What is 2+2?", decision, [], [], client=fake)

    assert resp.route == "none"
    assert resp.sources == []
    assert fake.last_context_blocks == []  # LLM.answer was never called
    assert "don't have enough information" in resp.answer
