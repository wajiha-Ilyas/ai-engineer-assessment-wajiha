"""Async client for the Superhero API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.config import settings
from app.errors import UpstreamError, UpstreamTimeout

logger = logging.getLogger(__name__)

BASE_URL = "https://superheroapi.com/api"
TIMEOUT = httpx.Timeout(10.0, connect=3.0)


@dataclass
class SuperheroResult:
    name: str
    biography: dict
    powerstats: dict
    appearance: dict
    # Source URL with token redacted for safe client exposure
    source_url: str


async def search_superhero(name: str) -> SuperheroResult | None:
    """
    Fetch the top matching superhero for *name* from the Superhero API.
    Returns None when the API reports no results.
    Raises UpstreamError / UpstreamTimeout on failures.
    """
    token = settings.superhero_api_token
    encoded = quote(name)
    url = f"{BASE_URL}/{token}/search/{encoded}"
    redacted_url = f"{BASE_URL}/REDACTED/search/{encoded}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
    except httpx.TimeoutException as exc:
        logger.warning("Superhero API timeout for %r", name)
        raise UpstreamTimeout("superhero_api") from exc
    except httpx.RequestError as exc:
        logger.warning("Superhero API request error for %r: %s", name, exc)
        raise UpstreamError("superhero_api", str(exc)) from exc

    if resp.status_code != 200:
        raise UpstreamError("superhero_api", f"HTTP {resp.status_code}")

    data = resp.json()

    if data.get("response") != "success":
        # "error" response means no hero found — not an upstream failure
        logger.info("Superhero API: no results for %r", name)
        return None

    hero = data["results"][0]
    return SuperheroResult(
        name=hero.get("name", name),
        biography=hero.get("biography", {}),
        powerstats=hero.get("powerstats", {}),
        appearance=hero.get("appearance", {}),
        source_url=redacted_url,
    )
