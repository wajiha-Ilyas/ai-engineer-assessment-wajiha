"""Conversation memory store.

Supports two backends:
  - RedisStore   : persistent, recommended for production (set REDIS_URL).
  - InMemoryStore: in-process dict, used when REDIS_URL is empty or Redis is
                   unreachable. Not shared across workers or restarts.

Usage
-----
The store is created once during application startup (lifespan) and attached
to app.state.store.  Each request reads history before routing and writes the
new turn after synthesis.

History format
--------------
A list of OpenAI-compatible chat messages (role + content):
  [
    {"role": "user",      "content": "Who is Batman?"},
    {"role": "assistant", "content": "Batman is Bruce Wayne ..."},
    ...
  ]
Only the last MAX_TURNS * 2 messages are kept to stay within token limits.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

MAX_TURNS = 5          # keep last 5 exchanges = 10 messages
MAX_MESSAGES = MAX_TURNS * 2


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class ConversationStore:
    async def get(self, session_id: str) -> list[dict]:
        raise NotImplementedError

    async def append(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        pass

    async def ping(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------

class RedisStore(ConversationStore):
    def __init__(self, redis_url: str, ttl: int) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl
        self._prefix = "nova:session:"

    async def ping(self) -> bool:
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    async def get(self, session_id: str) -> list[dict]:
        try:
            raw = await self._client.get(f"{self._prefix}{session_id}")
            return json.loads(raw) if raw else []
        except Exception as exc:
            logger.warning("Redis get failed for %s: %s", session_id, exc)
            return []

    async def append(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        key = f"{self._prefix}{session_id}"
        try:
            raw = await self._client.get(key)
            history: list[dict] = json.loads(raw) if raw else []
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_msg})
            history = history[-MAX_MESSAGES:]
            await self._client.setex(key, self._ttl, json.dumps(history))
        except Exception as exc:
            logger.warning("Redis append failed for %s: %s", session_id, exc)

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

class InMemoryStore(ConversationStore):
    def __init__(self) -> None:
        self._store: dict[str, list[dict]] = {}

    async def get(self, session_id: str) -> list[dict]:
        return list(self._store.get(session_id, []))

    async def append(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        history = self._store.get(session_id, [])
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        self._store[session_id] = history[-MAX_MESSAGES:]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

async def create_store(redis_url: str, ttl: int) -> ConversationStore:
    """
    Try to create a RedisStore; fall back to InMemoryStore if the URL is
    empty or the connection check fails.
    """
    if redis_url:
        store = RedisStore(redis_url, ttl)
        if await store.ping():
            logger.info("Memory backend: Redis (%s)", redis_url)
            return store
        logger.warning("Redis unreachable — falling back to in-memory store")
        await store.close()
    else:
        logger.info("Memory backend: in-memory (REDIS_URL not set)")
    return InMemoryStore()
