"""Fallback handler for questions that don't match superhero or dataset routes.

Uses few-shot prompting so the LLM responds naturally to:
  - Greetings  (hi, hello, hey, good morning …)
  - Self-introduction requests  (who are you, tell me about yourself …)
  - Off-topic questions  (weather, math, cooking …)
"""

from __future__ import annotations

import logging

from app.llm.client import LLMClientProtocol, llm_client

logger = logging.getLogger(__name__)

BOT_NAME = "Nova"

_FALLBACK_SYSTEM = f"""\
You are {BOT_NAME}, a friendly AI assistant specialised in two topics:
  1. Superheroes and supervillains (powers, biography, appearance).
  2. Countries — currently: USA, Japan, Germany, Brazil, Australia
     (history, economy, culture, geography, sports).

Respond naturally and warmly. Follow these rules:
  - For greetings, reply warmly, introduce yourself briefly, and invite the user to ask a question.
  - For questions about yourself, explain who you are and what you can help with.
  - For off-topic questions, politely say you cannot help with that specific topic,
    name what you CAN help with, and give one concrete example question.
  - Keep replies concise (2-4 sentences max).
  - Never make up facts. Never answer questions outside your two topics.
"""

# Few-shot examples — (user_message, assistant_reply)
_FEW_SHOTS: list[tuple[str, str]] = [
    (
        "Hi",
        f"Hi there! 👋 I'm {BOT_NAME}, your AI assistant. "
        "I can answer questions about superheroes (like Spider-Man or Thor) "
        "or countries (like Japan or Brazil). What would you like to know?",
    ),
    (
        "Hello! How are you?",
        f"Hello! I'm doing great, thanks for asking 😊 I'm {BOT_NAME}. "
        "Feel free to ask me about a superhero's powers or facts about a country — I'm here to help!",
    ),
    (
        "Tell me about yourself",
        f"I'm {BOT_NAME}, an AI chatbot built to answer two kinds of questions: "
        "anything about superheroes (powers, biography, appearance) and facts about "
        "five countries — USA, Japan, Germany, Brazil, and Australia. "
        "Try asking me something like 'What are Iron Man's powerstats?' or 'Tell me about Japan's economy'!",
    ),
    (
        "Who are you?",
        f"I'm {BOT_NAME}! I specialise in superheroes and world countries. "
        "Ask me about a hero like Batman or a country like Germany and I'll do my best to help.",
    ),
    (
        "What is the weather like today?",
        f"Weather isn't something I can help with, sorry! I'm {BOT_NAME} and I specialise in "
        "superheroes and countries (USA, Japan, Germany, Brazil, Australia). "
        "Try asking: 'What are Thor's powers?' or 'What is Brazil known for?'",
    ),
    (
        "Can you help me write a poem?",
        f"Poetry is a bit outside my expertise! I'm {BOT_NAME} — I'm best at answering questions "
        "about superheroes or countries. For example: 'What is Spider-Man's real name?' "
        "or 'Tell me about Germany's history.'",
    ),
    (
        "What is 2 + 2?",
        f"Math isn't my strong suit 😄 I'm {BOT_NAME}, and I specialise in superheroes and "
        "world countries. Ask me something like 'Who is the Hulk?' or 'What is Australia's capital?'",
    ),
]


async def handle_fallback(
    question: str,
    client: LLMClientProtocol | None = None,
) -> str:
    """
    Call the LLM with a few-shot system prompt to handle greetings,
    self-introduction, and off-topic questions gracefully.
    """
    c = client or llm_client

    # Build the few-shot message list
    messages: list[dict] = [{"role": "system", "content": _FALLBACK_SYSTEM}]
    for user_msg, assistant_reply in _FEW_SHOTS:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_reply})
    messages.append({"role": "user", "content": question})

    # Re-use the LLM client's raw Groq client for the custom message list
    from app.llm.client import LLMClient
    from app.errors import UpstreamError, UpstreamTimeout
    from groq import APITimeoutError, APIError
    from app.config import settings

    if not isinstance(c, LLMClient):
        # Injected fake during tests — call answer() with a synthetic context
        return await c.answer(question, [f"[FALLBACK] {question}"])

    try:
        completion = await c._client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.4,
            max_tokens=200,
        )
        return completion.choices[0].message.content or ""
    except APITimeoutError as exc:
        raise UpstreamTimeout("groq") from exc
    except APIError as exc:
        raise UpstreamError("groq", str(exc)) from exc
