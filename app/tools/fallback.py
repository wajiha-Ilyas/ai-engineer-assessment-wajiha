"""Fallback handler for questions that do not match superhero or dataset routes.

Uses few-shot prompting so the LLM responds naturally to greetings,
self-introduction requests, and off-topic questions.
Conversation history is injected so the bot remembers prior turns.
"""

from __future__ import annotations

import logging

from app.llm.client import LLMClientProtocol, llm_client

logger = logging.getLogger(__name__)

BOT_NAME = "Nova"

_FALLBACK_SYSTEM = (
    f"You are {BOT_NAME}, a friendly AI assistant specialised in two topics:\n"
    "  1. Superheroes and supervillains (powers, biography, appearance).\n"
    "  2. Countries - currently: USA, Japan, Germany, Brazil, Australia\n"
    "     (history, economy, culture, geography, sports).\n\n"
    "Follow these rules:\n"
    "  - For greetings, reply warmly, introduce yourself, invite a question.\n"
    "  - For self-intro requests, explain who you are and what you can help with.\n"
    "  - For off-topic questions, politely decline, name what you CAN answer, give an example.\n"
    "  - Keep replies concise (2-4 sentences). Never make up facts."
)

_FEW_SHOTS: list[tuple[str, str]] = [
    ("Hi", f"Hi there! I am {BOT_NAME}, your AI assistant. I can answer questions about superheroes like Spider-Man or countries like Japan. What would you like to know?"),
    ("Hello! How are you?", f"Hello! Doing great, thanks. I am {BOT_NAME}. Ask me about a superhero or a country and I will help!"),
    ("Tell me about yourself", f"I am {BOT_NAME}, an AI chatbot that answers questions about superheroes (powers, biography) and five countries: USA, Japan, Germany, Brazil, Australia. Try: What are Iron Man powerstats?"),
    ("Who are you?", f"I am {BOT_NAME}! I specialise in superheroes and world countries. Ask me about Batman or Germany and I will do my best."),
    ("What is the weather?", f"Weather is not something I can help with. I am {BOT_NAME} and I cover superheroes and countries. Try: What are Thor powers?"),
    ("Write me a poem", f"Poetry is outside my expertise. I am {BOT_NAME}, best at superheroes or countries. Try: What is Spider-Man real name?"),
    ("What is 2 plus 2?", f"Math is not my strong suit. I am {BOT_NAME}, covering superheroes and world countries. Ask: Who is the Hulk?"),
]


def _build_messages(question: str, history: list[dict] | None) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": _FALLBACK_SYSTEM}]
    for user_msg, assistant_reply in _FEW_SHOTS:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_reply})
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": question})
    return messages


async def handle_fallback(
    question: str,
    history: list[dict] | None = None,
    client: LLMClientProtocol | None = None,
) -> str:
    c = client or llm_client
    messages = _build_messages(question, history)
    return await c.chat(messages, temperature=0.4, max_tokens=200)
