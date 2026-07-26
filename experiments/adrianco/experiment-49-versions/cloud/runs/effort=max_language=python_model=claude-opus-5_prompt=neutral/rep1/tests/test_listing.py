"""Tests for the GET /books author filter and pagination."""

import pytest


@pytest.fixture
def library(make_book):
    """Three books by two different authors."""
    return [
        make_book(title="The Hobbit", author="J.R.R. Tolkien"),
        make_book(title="The Silmarillion", author="J.R.R. Tolkien"),
        make_book(title="Dune", author="Frank Herbert"),
    ]


def titles(response):
    return [book["title"] for book in response.get_json()]


def test_filter_by_author_returns_only_that_author(client, library):
    response = client.get("/books?author=J.R.R.+Tolkien")

    assert response.status_code == 200
    assert titles(response) == ["The Hobbit", "The Silmarillion"]
    assert response.headers["X-Total-Count"] == "2"


def test_filter_by_author_is_case_insensitive(client, library):
    response = client.get("/books", query_string={"author": "frank herbert"})

    assert titles(response) == ["Dune"]


def test_filter_with_no_matches_returns_an_empty_list(client, library):
    response = client.get("/books", query_string={"author": "Ursula Le Guin"})

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_blank_author_filter_returns_everything(client, library):
    response = client.get("/books", query_string={"author": "   "})

    assert len(response.get_json()) == 3


def test_filter_ignores_deleted_books(client, library):
    client.delete(f"/books/{library[0]['id']}")

    response = client.get("/books", query_string={"author": "J.R.R. Tolkien"})

    assert titles(response) == ["The Silmarillion"]


def test_limit_and_offset_paginate(client, library):
    page = client.get("/books", query_string={"limit": 2})
    assert titles(page) == ["The Hobbit", "The Silmarillion"]
    assert page.headers["X-Total-Count"] == "3"

    next_page = client.get("/books", query_string={"limit": 2, "offset": 2})
    assert titles(next_page) == ["Dune"]


def test_filter_and_pagination_combine(client, library):
    """The author filter and LIMIT/OFFSET share one parameter list."""
    response = client.get(
        "/books", query_string={"author": "J.R.R. Tolkien", "limit": 1, "offset": 1}
    )

    assert titles(response) == ["The Silmarillion"]
    assert response.headers["X-Total-Count"] == "2"


def test_offset_without_limit_skips_rows(client, library):
    response = client.get("/books", query_string={"offset": 1})

    assert titles(response) == ["The Silmarillion", "Dune"]


@pytest.mark.parametrize(
    "params",
    [{"limit": "many"}, {"limit": -1}, {"limit": 10001}, {"offset": -5}],
)
def test_invalid_pagination_parameters_are_rejected(client, params):
    response = client.get("/books", query_string=params)

    assert response.status_code == 400
    assert "error" in response.get_json()
