# AI Engineer Assessment — Wajiha Ilyas

A FastAPI chatbot that answers natural language questions using two sources: a curated text dataset and the [Superhero API](https://superheroapi.com). It routes each question to the right source (or both), calls a hosted LLM (Groq / Llama 3) to synthesize a grounded answer, and includes source attribution in every response.

---

## Setup

```bash
git clone https://github.com/<your-account>/ai-engineer-assessment-wajiha.git
cd ai-engineer-assessment-wajiha

python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env
# Fill in GROQ_API_KEY and SUPERHERO_API_TOKEN in .env
```

**Getting credentials (both free):**

| Key | Where to get it |
|-----|----------------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → sign up with email → API Keys |
| `SUPERHERO_API_TOKEN` | [superheroapi.com](https://superheroapi.com) → Sign in with GitHub |

---

## Run

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.

---

## Usage

```bash
curl -s http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are Spider-Man'\''s powerstats?"}' | jq
```

Example response:

```json
{
  "answer": "Spider-Man has the following powerstats: intelligence 90, strength 55, speed 67, durability 75, power 74, combat 85.",
  "route": "superhero",
  "sources": [
    {
      "kind": "superhero_api",
      "name": "Spider-Man",
      "url": "https://superheroapi.com/api/REDACTED/search/Spider-Man"
    }
  ]
}
```

---

## Tests

```bash
pytest -q
```

---

## Architecture

Two-stage LLM pipeline:

1. **Router** — classifies the question as `superhero`, `dataset`, `both`, or `none` using Groq in JSON mode.
2. **Tools** — fetches context in parallel: Superhero API and/or TF-IDF retrieval over the local text corpus.
3. **Synthesizer** — grounded prompt with tagged context blocks; model cites sources by tag.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for full architecture, trade-off decisions, and build order.
