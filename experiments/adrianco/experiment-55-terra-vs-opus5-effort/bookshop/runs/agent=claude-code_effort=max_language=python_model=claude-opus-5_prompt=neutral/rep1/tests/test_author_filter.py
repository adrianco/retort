"""``GET /books?author=`` behaviour."""

from __future__ import annotations

import pytest


@pytest.fixture
def collection(client):
    for title, author in [
        ("A Wizard of Earthsea", "Ursula K. Le Guin"),
        ("The Tombs of Atuan", "Ursula K. Le Guin"),
        ("Dune", "Frank Herbert"),
    ]:
        assert client.post("/books", json={"title": title, "author": author}).status_code == 201
    return client


def _titles(response):
    return [book["title"] for book in response.get_json()]


def test_filter_returns_only_that_authors_books(collection):
    response = collection.get("/books?author=Ursula K. Le Guin")

    assert response.status_code == 200
    assert _titles(response) == ["A Wizard of Earthsea", "The Tombs of Atuan"]


def test_filter_is_case_insensitive(collection):
    response = collection.get("/books?author=ursula k. LE GUIN")

    assert _titles(response) == ["A Wizard of Earthsea", "The Tombs of Atuan"]


def test_filter_ignores_surrounding_whitespace(collection):
    response = collection.get("/books?author=%20Frank%20Herbert%20")

    assert _titles(response) == ["Dune"]


def test_filter_is_an_exact_match_not_a_substring(collection):
    assert _titles(collection.get("/books?author=Herbert")) == []


def test_unknown_author_returns_empty_list(collection):
    response = collection.get("/books?author=Nobody")

    assert response.status_code == 200
    assert response.get_json() == []


def test_blank_filter_returns_everything(collection):
    assert len(_titles(collection.get("/books?author="))) == 3
    assert len(_titles(collection.get("/books"))) == 3


def test_filter_does_not_allow_sql_injection(collection):
    response = collection.get("/books?author=' OR 1=1 --")

    assert response.status_code == 200
    assert response.get_json() == []
    # The table is still there afterwards.
    assert len(collection.get("/books").get_json()) == 3
