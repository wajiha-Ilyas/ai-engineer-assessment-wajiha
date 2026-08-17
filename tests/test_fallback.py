"""Tests for the fallback handler (greetings, self-intro, off-topic)."""

import pytest

from app.llm.client import RouteDecision
from app.tools.fallback import handle_fallback, BOT_NAME


class FakeLLMClient:
    """Returns a controllable answer and records calls."""

    def __init__(self, reply: str = "fake fallback reply"):
        self._reply = reply
        self.last_messages: list[dict] | None = None

    async def route(self, question: str) -> RouteDecision:
        return RouteDecision(route="none")

    async def answer(self, question: str, context_blocks: list[str], history=None) -> str:
        return self._reply

    async def chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 200) -> str:
        self.last_messages = messages
        return self._reply


@pytest.mark.asyncio
async def test_fallback_calls_chat_with_messages():
    fake = FakeLLMClient(reply="Hi! I am Nova.")
    result = await handle_fallback("Hello there", client=fake)
    assert result == "Hi! I am Nova."
    # chat() must have been called with a list of messages
    assert fake.last_messages is not None
    assert any(m["content"] == "Hello there" for m in fake.last_messages)


@pytest.mark.asyncio
async def test_fallback_includes_history():
    fake = FakeLLMClient(reply="I remember you asked about Batman.")
    history = [
        {"role": "user", "content": "Who is Batman?"},
        {"role": "assistant", "content": "Batman is Bruce Wayne."},
    ]
    await handle_fallback("Tell me more", history=history, client=fake)
    # History messages should appear in the chat messages
    contents = [m["content"] for m in fake.last_messages]
    assert "Who is Batman?" in contents


@pytest.mark.asyncio
async def test_fallback_returns_string():
    fake = FakeLLMClient(reply="I am Nova, your AI assistant.")
    result = await handle_fallback("Tell me about yourself", client=fake)
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.asyncio
async def test_bot_name_defined():
    assert BOT_NAME and isinstance(BOT_NAME, str)
