"""Tests for the fallback handler (greetings, self-intro, off-topic)."""

import pytest

from app.llm.client import RouteDecision
from app.tools.fallback import handle_fallback, BOT_NAME


class FakeLLMClient:
    """Returns a controllable answer and records the call."""

    def __init__(self, reply: str = "fake fallback reply"):
        self._reply = reply
        self.called_with: str | None = None

    async def route(self, question: str) -> RouteDecision:
        return RouteDecision(route="none")

    async def answer(self, question: str, context_blocks: list[str]) -> str:
        self.called_with = question
        return self._reply


@pytest.mark.asyncio
async def test_fallback_called_with_question():
    fake = FakeLLMClient(reply="Hi! I'm Nova.")
    result = await handle_fallback("Hello there", client=fake)
    assert result == "Hi! I'm Nova."
    assert fake.called_with == "Hello there"


@pytest.mark.asyncio
async def test_fallback_returns_string():
    fake = FakeLLMClient(reply="I'm Nova, your AI assistant.")
    result = await handle_fallback("Tell me about yourself", client=fake)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_bot_name_defined():
    """Bot name constant should be set."""
    assert BOT_NAME and isinstance(BOT_NAME, str)
