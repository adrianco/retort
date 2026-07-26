"""Tests for GET /books, including the ?author= filter and pagination."""

from __future__ import annotations


def titles(response):
    return [book["title"] for book in response.get_json()]


def test_listing_an_empty_collection_returns_an_empty_array(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_listing_returns_every_book(client, library):
    response = client.get("/books")

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, list)
    assert len(body) == len(library)
    assert body == library  # default ordering is by ascending id
    assert response.headers["X-Total-Count"] == str(len(library))


def test_filtering_by_author_returns_only_that_author(client, library):
    response = client.get("/books?author=Frank Herbert")

    assert response.status_code == 200
    assert titles(response) == ["Dune", "Children of Dune"]
    assert response.headers["X-Total-Count"] == "2"


def test_the_author_filter_ignores_case(client, library):
    response = client.get("/books?author=frank HERBERT")

    assert titles(response) == ["Dune", "Children of Dune"]


def test_the_author_filter_matches_the_whole_name(client, library):
    response = client.get("/books?author=Herbert")

    assert response.status_code == 200
    assert response.get_json() == []


def test_an_unknown_author_yields_an_empty_array(client, library):
    response = client.get("/books?author=Nobody At All")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_a_blank_author_filter_is_ignored(client, library):
    response = client.get("/books?author=   ")

    assert len(response.get_json()) == len(library)


def test_filtering_by_year(client, library):
    response = client.get("/books?year=1984")

    assert titles(response) == ["Neuromancer"]


def test_the_q_parameter_searches_titles_and_authors(client, library):
    assert titles(client.get("/books?q=dune")) == ["Dune", "Children of Dune"]
    assert titles(client.get("/books?q=gibson")) == ["Neuromancer"]


def test_the_q_parameter_treats_wildcards_literally(client, library):
    response = client.get("/books?q=%25")  # a bare SQL "%" wildcard

    assert response.get_json() == []


def test_filters_combine(client, library):
    response = client.get("/books?author=Frank Herbert&year=1976")

    assert titles(response) == ["Children of Dune"]


def test_sorting_by_title(client, library):
    assert titles(client.get("/books?sort=title")) == [
        "A Wizard of Earthsea",
        "Children of Dune",
        "Dune",
        "Neuromancer",
    ]


def test_sorting_descending_with_a_minus_prefix(client, library):
    assert titles(client.get("/books?sort=-year")) == [
        "Neuromancer",
        "Children of Dune",
        "A Wizard of Earthsea",
        "Dune",
    ]


def test_pagination_slices_the_collection(client, library):
    page = client.get("/books?limit=2&offset=1")

    assert titles(page) == ["Children of Dune", "Neuromancer"]
    assert page.headers["X-Total-Count"] == str(len(library))
    assert page.headers["X-Limit"] == "2"
    assert page.headers["X-Offset"] == "1"


def test_an_offset_past_the_end_returns_an_empty_page(client, library):
    response = client.get("/books?offset=99")

    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == str(len(library))


def test_pagination_respects_the_active_filter(client, library):
    response = client.get("/books?author=Frank Herbert&limit=1")

    assert titles(response) == ["Dune"]
    assert response.headers["X-Total-Count"] == "2"


def test_deleted_books_disappear_from_the_listing(client, library):
    client.delete("/books/{}".format(library[0]["id"]))

    response = client.get("/books")

    assert len(response.get_json()) == len(library) - 1
    assert response.headers["X-Total-Count"] == str(len(library) - 1)
