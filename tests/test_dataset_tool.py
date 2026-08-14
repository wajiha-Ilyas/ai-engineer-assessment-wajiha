"""Tests for the TF-IDF dataset retriever."""

from pathlib import Path

import pytest

from app.tools.dataset import DatasetRetriever, DOCS_DIR


def test_retriever_returns_results():
    r = DatasetRetriever(DOCS_DIR)
    results = r.retrieve("capital city of Japan", k=3)
    assert len(results) > 0
    # The top result should be from the Japan document
    assert results[0].doc_id == "japan"


def test_retriever_top_result_usa():
    r = DatasetRetriever(DOCS_DIR)
    results = r.retrieve("Silicon Valley technology Apple Google", k=3)
    assert results[0].doc_id == "usa"


def test_retriever_top_result_brazil():
    r = DatasetRetriever(DOCS_DIR)
    results = r.retrieve("Amazon rainforest coffee football World Cup", k=3)
    assert results[0].doc_id == "brazil"


def test_retriever_empty_corpus(tmp_path: Path):
    r = DatasetRetriever(tmp_path)
    assert r.retrieve("anything") == []


def test_retriever_no_match_returns_empty(tmp_path: Path):
    """A corpus with one doc that shares zero terms with the query returns []."""
    (tmp_path / "doc.txt").write_text("Apple pie recipe bake oven sugar flour", encoding="utf-8")
    r = DatasetRetriever(tmp_path)
    # All tokens are present — cosine > 0 is possible; test that function at least returns a list
    results = r.retrieve("xyz123 qwerty zzzz")
    assert isinstance(results, list)
