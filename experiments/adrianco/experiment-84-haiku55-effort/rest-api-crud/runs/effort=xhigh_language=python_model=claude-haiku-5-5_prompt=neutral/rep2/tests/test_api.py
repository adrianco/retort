import json

import pytest

from bookapi import BookRepository, BooksApi

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": None}
CHILDREN = {"title": "Children of Dune", "author": "Frank Herbert", "year": 1976, "isbn": None}


def encode(payload):
    return json.dumps(payload).encode("utf-8")


@pytest.fixture
def api():
    instance = BooksApi(BookRepository(":memory:"))
    yield instance
    instance.close()


def create(api, payload=DUNE):
    response = api.handle("POST", "/books", encode(payload))
    assert response.status == 201, response.body
    return response.body


def test_create_returns_201_with_location_and_stored_book(api):
    response = api.handle("POST", "/books", encode(DUNE))

    assert response.status == 201
    assert response.body == {"id": response.body["id"], **DUNE}
    assert response.headers["Location"] == f"/books/{response.body['id']}"


def test_created_book_can_be_fetched_by_id(api):
    book = create(api)

    response = api.handle("GET", f"/books/{book['id']}")

    assert response.status == 200
    assert response.body == book


def test_create_rejects_missing_title_and_stores_nothing(api):
    response = api.handle("POST", "/books", encode({"author": "Frank Herbert"}))

    assert response.status == 400
    assert response.body == {"error": "Validation failed", "details": {"title": "is required"}}
    assert api.handle("GET", "/books").body == []


@pytest.mark.parametrize("raw", [b"", b"{not json", b"[1, 2]"])
def test_create_rejects_bodies_that_are_not_a_book_object(api, raw):
    response = api.handle("POST", "/books", raw)

    assert response.status == 400
    assert "error" in response.body


def test_list_returns_every_book_in_id_order(api):
    create(api, DUNE)
    create(api, EMMA)

    response = api.handle("GET", "/books")

    assert response.status == 200
    assert [book["title"] for book in response.body] == ["Dune", "Emma"]


def test_list_filters_by_author_ignoring_case(api):
    create(api, DUNE)
    create(api, EMMA)
    create(api, CHILDREN)

    frank = api.handle("GET", "/books?author=frank%20herbert").body
    austen = api.handle("GET", "/books?author=Austen").body
    nobody = api.handle("GET", "/books?author=Tolkien").body

    assert [book["title"] for book in frank] == ["Dune", "Children of Dune"]
    assert [book["title"] for book in austen] == ["Emma"]
    assert nobody == []


def test_author_filter_folds_non_ascii_case(api):
    create(api, {"title": "Cien años", "author": "Gabriel García Márquez"})

    # %C3%AD is the percent-encoded UTF-8 for "í" and %C3%A1 for "á".
    found = api.handle("GET", "/books?author=GARC%C3%8DA%20M%C3%81RQUEZ").body

    assert [book["title"] for book in found] == ["Cien años"]


@pytest.mark.parametrize("query", ["/books?author=", "/books?author=%20", "/books"])
def test_blank_or_missing_author_filter_returns_everything(api, query):
    create(api, DUNE)
    create(api, EMMA)

    assert len(api.handle("GET", query).body) == 2


def test_get_unknown_book_returns_404(api):
    response = api.handle("GET", "/books/999")

    assert response.status == 404
    assert response.body == {"error": "Book not found"}


@pytest.mark.parametrize("path", ["/books/abc", "/books/-1", "/books/99999999999999999999999"])
def test_malformed_or_oversized_ids_are_not_found(api, path):
    assert api.handle("GET", path).status == 404


def test_put_replaces_every_field(api):
    book = create(api, DUNE)
    replacement = {"title": "Dune Messiah", "author": "Frank Herbert"}

    response = api.handle("PUT", f"/books/{book['id']}", encode(replacement))

    assert response.status == 200
    assert response.body == {"id": book["id"], "title": "Dune Messiah",
                             "author": "Frank Herbert", "year": None, "isbn": None}
    assert api.handle("GET", f"/books/{book['id']}").body == response.body


def test_put_validates_the_body_and_leaves_book_unchanged(api):
    book = create(api, DUNE)

    response = api.handle("PUT", f"/books/{book['id']}", encode({"title": "New"}))

    assert response.status == 400
    assert response.body["details"] == {"author": "is required"}
    assert api.handle("GET", f"/books/{book['id']}").body == book


def test_put_unknown_book_returns_404(api):
    response = api.handle("PUT", "/books/404", encode(DUNE))

    assert response.status == 404


def test_delete_removes_the_book(api):
    book = create(api)

    response = api.handle("DELETE", f"/books/{book['id']}")

    assert response.status == 204
    assert response.body is None
    assert api.handle("GET", f"/books/{book['id']}").status == 404


def test_delete_unknown_book_returns_404(api):
    assert api.handle("DELETE", "/books/404").status == 404


def test_health_reports_ok(api):
    response = api.handle("GET", "/health")

    assert response.status == 200
    assert response.body == {"status": "ok"}


def test_health_reports_unavailable_when_database_is_closed(api):
    api.repo.close()

    response = api.handle("GET", "/health")

    assert response.status == 503
    assert response.body == {"status": "unavailable"}


def test_unknown_path_returns_404(api):
    assert api.handle("GET", "/authors").status == 404
    assert api.handle("GET", "/").status == 404


def test_wrong_method_returns_405_with_allow_header(api):
    book = create(api)

    on_book = api.handle("PATCH", f"/books/{book['id']}")
    on_collection = api.handle("DELETE", "/books")

    assert on_book.status == 405
    assert on_book.headers["Allow"] == "DELETE, GET, PUT"
    assert on_collection.status == 405
    assert on_collection.headers["Allow"] == "GET, POST"


def test_trailing_slash_is_ignored(api):
    create(api)

    assert api.handle("GET", "/books/").status == 200


def test_unexpected_failures_become_500(api):
    class BrokenRepository:
        def search(self, author=None):
            raise RuntimeError("disk on fire")

    response = BooksApi(BrokenRepository()).handle("GET", "/books")

    assert response.status == 500
    assert response.body == {"error": "Internal server error"}


def test_data_persists_across_restarts(tmp_path):
    db_path = str(tmp_path / "books.db")
    first = BooksApi(BookRepository(db_path))
    created = create(first)
    first.close()

    second = BooksApi(BookRepository(db_path))
    try:
        assert second.handle("GET", f"/books/{created['id']}").body == created
    finally:
        second.close()
