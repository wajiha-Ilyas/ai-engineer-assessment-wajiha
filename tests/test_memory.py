"""Tests for the conversation memory store."""

import pytest

from app.memory import InMemoryStore, MAX_MESSAGES


@pytest.mark.asyncio
async def test_get_empty_session():
    store = InMemoryStore()
    history = await store.get("session-abc")
    assert history == []


@pytest.mark.asyncio
async def test_append_and_get():
    store = InMemoryStore()
    await store.append("s1", "Who is Batman?", "Batman is Bruce Wayne.")
    history = await store.get("s1")
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Who is Batman?"}
    assert history[1] == {"role": "assistant", "content": "Batman is Bruce Wayne."}


@pytest.mark.asyncio
async def test_sessions_are_isolated():
    store = InMemoryStore()
    await store.append("s1", "Q1", "A1")
    await store.append("s2", "Q2", "A2")
    assert len(await store.get("s1")) == 2
    assert len(await store.get("s2")) == 2
    # s1 should not have s2's messages
    assert all(m["content"] in ("Q1", "A1") for m in await store.get("s1"))


@pytest.mark.asyncio
async def test_history_capped_at_max_messages():
    store = InMemoryStore()
    # Add more than MAX_MESSAGES / 2 turns
    for i in range(MAX_MESSAGES):
        await store.append("s1", f"Q{i}", f"A{i}")
    history = await store.get("s1")
    assert len(history) == MAX_MESSAGES


@pytest.mark.asyncio
async def test_get_returns_copy():
    """Mutating the returned list must not affect stored history."""
    store = InMemoryStore()
    await store.append("s1", "Q", "A")
    h1 = await store.get("s1")
    h1.append({"role": "user", "content": "injected"})
    h2 = await store.get("s1")
    assert len(h2) == 2  # unchanged
