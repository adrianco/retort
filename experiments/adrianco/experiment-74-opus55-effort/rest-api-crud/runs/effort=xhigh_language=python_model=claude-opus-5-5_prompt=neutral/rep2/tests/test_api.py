"""Endpoint behaviour, exercised through BooksApp.handle without a network socket."""

import pytest

from books_api import BookRepository, BooksApp

from .samples import ANIMAL_FARM, HUXLEY, ORWELL


@pytest.fixture
def create(call):
    def _create(book):
        result = call("POST", "/books", book)
        assert result.status == 201, result.json
        return result.json

    return _create


# -- health -----------------------------------------------------------------


def test_health(call):
    result = call("GET", "/health")
    assert result.status == 200
    assert result.json == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_database(repo, call):
    repo.close()
    result = call("GET", "/health")
    assert result.status == 503
    assert result.json["status"] == "unavailable"


# -- POST /books ------------------------------------------------------------


def test_create_book(call):
    result = call("POST", "/books", ORWELL)
    assert result.status == 201
    assert result.json == {"id": 1, **ORWELL}
    assert result.headers["Location"] == "/books/1"


def test_create_book_with_only_required_fields(call):
    result = call("POST", "/books", {"title": "Beowulf", "author": "Unknown"})
    assert result.status == 201
    assert result.json == {"id": 1, "title": "Beowulf", "author": "Unknown", "year": None, "isbn": None}


def test_create_trims_whitespace_and_ignores_client_id(call):
    result = call("POST", "/books", {"id": 42, "title": "  Dune ", "author": " Frank Herbert "})
    assert result.status == 201
    assert result.json["id"] == 1
    assert (result.json["title"], result.json["author"]) == ("Dune", "Frank Herbert")


@pytest.mark.parametrize(
    ("payload", "bad_fields"),
    [
        ({"author": "George Orwell"}, {"title"}),
        ({"title": "1984"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "", "author": "   "}, {"title", "author"}),
        ({"title": None, "author": "x"}, {"title"}),
        ({"title": 1984, "author": "George Orwell"}, {"title"}),
        ({**ORWELL, "year": "1949"}, {"year"}),
        ({**ORWELL, "isbn": "not-an-isbn"}, {"isbn"}),
    ],
)
def test_create_rejects_invalid_books(call, payload, bad_fields):
    result = call("POST", "/books", payload)
    assert result.status == 400
    assert result.json["error"] == "Validation failed"
    assert set(result.json["details"]) == bad_fields
    assert call("GET", "/books").json == []  # nothing was stored


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        (b"", "Request body must be a JSON object"),
        (b"{not json", "Request body is not valid JSON"),
        (b'{"title": "x", "author": "y", "year": NaN}', "Request body is not valid JSON"),
        (b"\xff\xfe\x00", "Request body is not valid JSON"),
        (b'["1984", "George Orwell"]', "Validation failed"),
    ],
)
def test_create_rejects_malformed_bodies(call, raw, error):
    result = call("POST", "/books", raw=raw)
    assert result.status == 400
    assert result.json["error"] == error


# -- GET /books -------------------------------------------------------------


def test_list_books_empty(call):
    result = call("GET", "/books")
    assert result.status == 200
    assert result.json == []


def test_list_books(call, create):
    created = [create(book) for book in (ORWELL, HUXLEY, ANIMAL_FARM)]
    result = call("GET", "/books")
    assert result.status == 200
    assert result.json == created


@pytest.mark.parametrize(
    ("query", "titles"),
    [
        ("author=George%20Orwell", ["1984", "Animal Farm"]),
        ("author=george+orwell", ["1984", "Animal Farm"]),
        ("author=HUXLEY", ["Brave New World"]),
        ("author=Tolstoy", []),
        ("author=", ["1984", "Brave New World", "Animal Farm"]),
        ("author=%20%20", ["1984", "Brave New World", "Animal Farm"]),
        ("other=ignored", ["1984", "Brave New World", "Animal Farm"]),
    ],
)
def test_list_books_filtered_by_author(call, create, query, titles):
    for book in (ORWELL, HUXLEY, ANIMAL_FARM):
        create(book)
    result = call("GET", f"/books?{query}")
    assert result.status == 200
    assert [b["title"] for b in result.json] == titles


# -- GET /books/{id} --------------------------------------------------------


def test_get_book(call, create):
    book = create(ORWELL)
    result = call("GET", f"/books/{book['id']}")
    assert result.status == 200
    assert result.json == book


@pytest.mark.parametrize("book_id", ["999", "0", "abc", "-1", "1.5", str(2**63), "9" * 40])
def test_get_unknown_book_is_404(call, create, book_id):
    create(ORWELL)
    result = call("GET", f"/books/{book_id}")
    assert result.status == 404
    assert result.json == {"error": "Book not found"}


# -- PUT /books/{id} --------------------------------------------------------


def test_update_book_with_full_representation(call, create):
    book = create(ORWELL)
    replacement = {"title": "Nineteen Eighty-Four", "author": "Eric Blair", "year": 1950, "isbn": "0451524934"}
    result = call("PUT", f"/books/{book['id']}", replacement)
    assert result.status == 200
    assert result.json == {"id": book["id"], **replacement}
    assert call("GET", f"/books/{book['id']}").json == result.json


def test_update_book_with_some_fields_keeps_the_others(call, create):
    book = create(ORWELL)
    result = call("PUT", f"/books/{book['id']}", {"year": 1950})
    assert result.status == 200
    assert result.json == {**book, "year": 1950}


def test_update_can_clear_optional_fields(call, create):
    book = create(ORWELL)
    result = call("PUT", f"/books/{book['id']}", {"year": None, "isbn": None})
    assert result.status == 200
    assert result.json == {**book, "year": None, "isbn": None}


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"author": None}, {"title": "ok", "year": "1950"}, {}, {"unknown": "field"}, ["title"]],
)
def test_update_rejects_invalid_changes(call, create, payload):
    book = create(ORWELL)
    result = call("PUT", f"/books/{book['id']}", payload)
    assert result.status == 400
    assert "details" in result.json
    assert call("GET", f"/books/{book['id']}").json == book  # unchanged


def test_update_rejects_invalid_json(call, create):
    book = create(ORWELL)
    assert call("PUT", f"/books/{book['id']}", raw=b"{").status == 400


def test_update_unknown_book_is_404(call):
    result = call("PUT", "/books/999", ORWELL)
    assert result.status == 404
    assert result.json == {"error": "Book not found"}


# -- DELETE /books/{id} -----------------------------------------------------


def test_delete_book(call, create):
    book = create(ORWELL)
    other = create(HUXLEY)

    result = call("DELETE", f"/books/{book['id']}")
    assert result.status == 204
    assert result.json is None

    assert call("GET", f"/books/{book['id']}").status == 404
    assert call("GET", "/books").json == [other]
    assert call("DELETE", f"/books/{book['id']}").status == 404


def test_deleted_ids_are_not_reused(call, create):
    book = create(ORWELL)
    call("DELETE", f"/books/{book['id']}")
    assert create(HUXLEY)["id"] != book["id"]


# -- routing ----------------------------------------------------------------


@pytest.mark.parametrize("target", ["/", "/book", "/books/1/extra", "/healthz"])
def test_unknown_routes_are_404(call, target):
    result = call("GET", target)
    assert result.status == 404
    assert result.json == {"error": "Not found"}


@pytest.mark.parametrize(
    ("method", "target", "allow"),
    [
        ("DELETE", "/books", "GET, HEAD, OPTIONS, POST"),
        ("PATCH", "/books/1", "DELETE, GET, HEAD, OPTIONS, PUT"),
        ("POST", "/health", "GET, HEAD, OPTIONS"),
    ],
)
def test_wrong_method_is_405_with_allow_header(call, create, method, target, allow):
    create(ORWELL)
    result = call(method, target, {})
    assert result.status == 405
    assert result.headers["Allow"] == allow
    assert "error" in result.json


def test_head_is_answered_like_get(call, create):
    book = create(ORWELL)
    result = call("HEAD", f"/books/{book['id']}")
    assert (result.status, result.json) == (200, book)  # the HTTP layer drops the body
    assert call("HEAD", "/books/999").status == 404


def test_options_lists_allowed_methods(call):
    result = call("OPTIONS", "/books")
    assert result.status == 204
    assert result.headers["Allow"] == "GET, HEAD, OPTIONS, POST"


def test_trailing_slashes_are_accepted(call, create):
    book = create(ORWELL)
    assert call("GET", "/books/").json == [book]
    assert call("GET", f"/books/{book['id']}/").json == book
    assert call("GET", "/health/").status == 200


def test_unexpected_errors_become_json_500():
    class BrokenRepository(BookRepository):
        def list_books(self, author=None):
            raise RuntimeError("boom")

    with BrokenRepository() as repository:
        response = BooksApp(repository).handle("GET", "/books")
    assert response.status == 500
    assert response.payload == {"error": "Internal server error"}
