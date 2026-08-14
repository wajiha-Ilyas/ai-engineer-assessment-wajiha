"""End-to-end tests for POST /ask — all upstreams mocked."""

import pytest
import respx
from httpx import AsyncClient, ASGITransport, Response

from app.main import app
from app.tools.superhero import BASE_URL

FAKE_TOKEN = "testtoken999"

HERO_PAYLOAD = {
    "response": "success",
    "results": [
        {
            "name": "Spider-Man",
            "powerstats": {"intelligence": "90", "strength": "55"},
            "biography": {"full-name": "Peter Parker"},
            "appearance": {"gender": "Male"},
        }
    ],
}

NO_HERO_PAYLOAD = {"response": "error", "error": "character not found"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_groq_route(respx_mock, route: str, names: list[str] = [], query: str = ""):
    import json
    body = json.dumps({"route": route, "superhero_names": names, "dataset_query": query})
    respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": body, "role": "assistant"}}],
                "model": "llama-3.1-8b-instant",
                "usage": {},
            },
        )
    )


def _mock_groq_answer(respx_mock, answer: str):
    respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": answer, "role": "assistant"}}],
                "model": "llama-3.1-8b-instant",
                "usage": {},
            },
        )
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ask_validation_empty_question():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ask", json={"question": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_validation_missing_field():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ask", json={})
    assert resp.status_code == 422


@respx.mock
@pytest.mark.asyncio
async def test_ask_superhero_only(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)

    # First Groq call → router; second → answer
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        side_effect=[
            Response(200, json={
                "choices": [{"message": {"content": '{"route":"superhero","superhero_names":["Spider-Man"],"dataset_query":""}', "role": "assistant"}}],
                "model": "x", "usage": {},
            }),
            Response(200, json={
                "choices": [{"message": {"content": "Spider-Man is Peter Parker. (S1)", "role": "assistant"}}],
                "model": "x", "usage": {},
            }),
        ]
    )
    respx.get(f"{BASE_URL}/{FAKE_TOKEN}/search/Spider-Man").mock(
        return_value=Response(200, json=HERO_PAYLOAD)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ask", json={"question": "Who is Spider-Man?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "superhero"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["kind"] == "superhero_api"
    assert FAKE_TOKEN not in body["sources"][0]["url"]


@respx.mock
@pytest.mark.asyncio
async def test_ask_dataset_only(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)

    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        side_effect=[
            Response(200, json={
                "choices": [{"message": {"content": '{"route":"dataset","superhero_names":[],"dataset_query":"capital of Japan"}', "role": "assistant"}}],
                "model": "x", "usage": {},
            }),
            Response(200, json={
                "choices": [{"message": {"content": "The capital of Japan is Tokyo. (S1)", "role": "assistant"}}],
                "model": "x", "usage": {},
            }),
        ]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ask", json={"question": "What is the capital of Japan?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "dataset"
    assert all(s["kind"] == "dataset" for s in body["sources"])


@respx.mock
@pytest.mark.asyncio
async def test_ask_llm_upstream_failure_returns_502(monkeypatch):
    monkeypatch.setattr("app.tools.superhero.settings.superhero_api_token", FAKE_TOKEN)
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=Response(500, json={"error": "internal"})
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ask", json={"question": "Tell me something."})

    assert resp.status_code == 502
