"""TF-IDF retriever over the local text corpus in data/docs/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs"
CHUNK_SIZE = 500   # characters
CHUNK_OVERLAP = 100


@dataclass
class Chunk:
    doc_id: str    # filename without extension, e.g. "usa"
    chunk_id: int
    title: str     # first line of the document
    text: str


def _split_into_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        start += size - overlap
    return [c for c in chunks if c]


def _load_docs(docs_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.txt")):
        raw = path.read_text(encoding="utf-8").strip()
        # First non-empty line is the title
        title = next((ln.strip() for ln in raw.splitlines() if ln.strip()), path.stem)
        doc_id = path.stem
        for i, chunk_text in enumerate(_split_into_chunks(raw)):
            chunks.append(Chunk(doc_id=doc_id, chunk_id=i, title=title, text=chunk_text))
    return chunks


class DatasetRetriever:
    """Build a TF-IDF index at construction time and expose a retrieve() method."""

    def __init__(self, docs_dir: Path = DOCS_DIR) -> None:
        self._chunks = _load_docs(docs_dir)
        if not self._chunks:
            self._vectorizer = None
            self._matrix = None
            return
        self._vectorizer = TfidfVectorizer(
            strip_accents="unicode",
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
        )
        texts = [c.text for c in self._chunks]
        self._matrix = self._vectorizer.fit_transform(texts)

    def retrieve(self, query: str, k: int = 3) -> list[Chunk]:
        """Return the top-k most relevant chunks for the query."""
        if self._vectorizer is None or self._matrix is None:
            return []
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = np.argsort(sims)[::-1][:k]
        return [self._chunks[i] for i in top_indices if sims[i] > 0]


# Module-level singleton — built once at startup.
retriever = DatasetRetriever()
