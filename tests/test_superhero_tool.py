"""Tests for the Superhero API tool (HTTP mocked with respx)."""

import pytest
import respx
from httpx import Response

from app.errors import UpstreamError, UpstreamTimeout
from app.tools.superhero import search_superhero, BASE_URL

FAKE_TOKEN = "abc123testtoken"

HERO_PAYLOAD = {
    "response": "success",
    "results-for": "Spider-Man",
    "results": [
        {
            "name": "Spider-Man",
            "powerstats": {"intelligence": "90", "strength": "55", "speed": "67"},
            "biography": {"full-name": "Peter Parker", "place-of-birth": "New York"},
            "appearance": {"gender": "Male", "height": ["5'10", "178 cm"]},
        }
    ],
}


@respx.mock
@pytest.mark.asyncio
async def test_search_superhero_success(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)
    respx.get(f"{BASE_URL}/{FAKE_TOKEN}/search/Spider-Man").mock(
        return_value=Response(200, json=HERO_PAYLOAD)
    )

    result = await search_superhero("Spider-Man")

    assert result is not None
    assert result.name == "Spider-Man"
    assert result.powerstats["intelligence"] == "90"
    assert result.biography["full-name"] == "Peter Parker"
    # Token must be redacted in source URL
    assert FAKE_TOKEN not in result.source_url
    assert "REDACTED" in result.source_url


@respx.mock
@pytest.mark.asyncio
async def test_search_superhero_not_found(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)
    respx.get(f"{BASE_URL}/{FAKE_TOKEN}/search/UnknownHero").mock(
        return_value=Response(200, json={"response": "error", "error": "character with given name not found"})
    )

    result = await search_superhero("UnknownHero")
    assert result is None


@respx.mock
@pytest.mark.asyncio
async def test_search_superhero_http_error(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)
    respx.get(f"{BASE_URL}/{FAKE_TOKEN}/search/Batman").mock(
        return_value=Response(500)
    )

    with pytest.raises(UpstreamError) as exc_info:
        await search_superhero("Batman")
    assert "HTTP 500" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_search_superhero_timeout(monkeypatch):
    import httpx
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)
    respx.get(f"{BASE_URL}/{FAKE_TOKEN}/search/Batman").mock(
        side_effect=httpx.ReadTimeout("timed out", request=None)
    )

    with pytest.raises(UpstreamTimeout):
        await search_superhero("Batman")
