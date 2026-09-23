import datetime

import pytest

from books_api.app import MAX_BODY_BYTES, MAX_BOOK_ID

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "0-14-143958-7"}
PERSUASION = {"title": "Persuasion", "author": "Jane Austen", "year": 1817}


def create(client, payload):
    response = client.post("/books", payload)
    assert response.status_code == 201, response.body
    return response.json()


# -- health -------------------------------------------------------------------


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_check_reports_unavailable_database(client, repository):
    repository.close()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


# -- create -------------------------------------------------------------------


def test_create_book(client):
    response = client.post("/books", DUNE)
    assert response.status_code == 201
    book = response.json()
    assert book == {"id": book["id"], **DUNE}
    assert isinstance(book["id"], int)
    assert response.headers["location"] == f"/books/{book['id']}"


def test_create_book_with_only_required_fields(client):
    book = create(client, {"title": "Dune", "author": "Frank Herbert"})
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_book_trims_whitespace_and_keeps_unicode(client):
    book = create(client, {"title": "  Cien años de soledad ", "author": "Gabriel García Márquez"})
    assert book["title"] == "Cien años de soledad"
    assert client.get(f"/books/{book['id']}").json()["author"] == "Gabriel García Márquez"


@pytest.mark.parametrize(
    "payload, expected_details",
    [
        ({}, {"title": "title is required", "author": "author is required"}),
        ({"author": "Frank Herbert"}, {"title": "title is required"}),
        ({"title": "Dune"}, {"author": "author is required"}),
        ({"title": "", "author": "Frank Herbert"}, {"title": "title must not be blank"}),
        ({"title": "Dune", "author": None}, {"author": "author is required"}),
        ({"title": 1965, "author": "Frank Herbert"}, {"title": "title must be a string"}),
    ],
)
def test_create_requires_title_and_author(client, payload, expected_details):
    response = client.post("/books", payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Validation failed", "details": expected_details}
    assert client.get("/books").json() == []


@pytest.mark.parametrize(
    "extra, field",
    [
        ({"year": "1965"}, "year"),
        ({"year": datetime.date.today().year + 1}, "year"),
        ({"isbn": "not-an-isbn"}, "isbn"),
        ({"genre": "sci-fi"}, "genre"),
    ],
)
def test_create_rejects_invalid_optional_fields(client, extra, field):
    response = client.post("/books", {"title": "Dune", "author": "Frank Herbert", **extra})
    assert response.status_code == 400
    assert list(response.json()["details"]) == [field]


@pytest.mark.parametrize(
    "body, message",
    [
        (b"", "Request body must be a JSON object"),
        (b"{not json", "Request body is not valid JSON"),
        (b"\xff\xfe\xfa", "Request body is not valid JSON"),
        (b"[" * 100_000, "Request body is not valid JSON"),
        (b'["Dune", "Frank Herbert"]', "Request body must be a JSON object"),
        (b'"Dune"', "Request body must be a JSON object"),
        (b"null", "Request body must be a JSON object"),
    ],
)
def test_create_rejects_malformed_bodies(client, body, message):
    response = client.post("/books", data=body)
    assert response.status_code == 400
    assert response.json() == {"error": message}


@pytest.mark.parametrize("content_type", [None, "text/plain", "application/x-www-form-urlencoded"])
def test_create_requires_json_content_type(client, content_type):
    response = client.post("/books", DUNE, content_type=content_type)
    assert response.status_code == 415
    assert response.json() == {"error": "Content-Type must be application/json"}


def test_create_accepts_json_content_type_with_parameters(client):
    response = client.post("/books", DUNE, content_type="application/json; charset=utf-8")
    assert response.status_code == 201


def test_create_rejects_oversized_body(client):
    response = client.post("/books", data=b" " * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413


def test_create_rejects_invalid_content_length(unvalidated_client):
    response = unvalidated_client.post("/books", DUNE, environ_overrides={"CONTENT_LENGTH": "abc"})
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid Content-Length header"}


def test_create_ignores_client_supplied_id(client):
    book = create(client, {"id": 999, **DUNE})
    assert book["id"] != 999
    assert client.get("/books/999").status_code == 404


# -- list ---------------------------------------------------------------------


def test_list_books_empty(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []


def test_list_books_returns_all_books_in_creation_order(client):
    created = [create(client, b) for b in (DUNE, EMMA, PERSUASION)]
    assert client.get("/books").json() == created


def test_list_books_filters_by_author(client):
    create(client, DUNE)
    emma = create(client, EMMA)
    persuasion = create(client, PERSUASION)

    assert client.get("/books?author=Jane%20Austen").json() == [emma, persuasion]
    assert client.get("/books?author=jane+austen").json() == [emma, persuasion]
    assert client.get("/books?author=austen").json() == [emma, persuasion]
    assert client.get("/books?author=Tolkien").json() == []


def test_list_books_with_blank_author_filter_returns_everything(client):
    created = [create(client, b) for b in (DUNE, EMMA)]
    assert client.get("/books?author=").json() == created
    assert client.get("/books?author=%20%20").json() == created


def test_list_books_ignores_unknown_query_parameters(client):
    book = create(client, DUNE)
    assert client.get("/books?sort=title").json() == [book]


def test_list_books_accepts_trailing_slash(client):
    book = create(client, DUNE)
    assert client.get("/books/").json() == [book]


# -- get ----------------------------------------------------------------------


def test_get_book(client):
    book = create(client, DUNE)
    response = client.get(f"/books/{book['id']}")
    assert response.status_code == 200
    assert response.json() == book


@pytest.mark.parametrize("book_id", ["42", "abc", "-1", "1.5", str(MAX_BOOK_ID + 1)])
def test_get_missing_book_returns_404(client, book_id):
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404
    assert "error" in response.json()


# -- update -------------------------------------------------------------------


def test_update_book(client):
    book = create(client, DUNE)
    changes = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "978-0-593-09823-5"}
    response = client.put(f"/books/{book['id']}", changes)
    assert response.status_code == 200
    assert response.json() == {"id": book["id"], **changes}
    assert client.get(f"/books/{book['id']}").json() == {"id": book["id"], **changes}


def test_update_replaces_the_whole_book(client):
    book = create(client, DUNE)
    response = client.put(f"/books/{book['id']}", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status_code == 200
    assert response.json() == {"id": book["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_update_accepts_a_book_as_returned_by_get(client):
    book = create(client, DUNE)
    edited = {**book, "year": 1966, "id": 12345}
    response = client.put(f"/books/{book['id']}", edited)
    assert response.status_code == 200
    assert response.json() == {**book, "year": 1966}


def test_update_validates_input_and_leaves_book_unchanged(client):
    book = create(client, DUNE)
    response = client.put(f"/books/{book['id']}", {"title": "  ", "year": 1965})
    assert response.status_code == 400
    assert set(response.json()["details"]) == {"title", "author"}
    assert client.get(f"/books/{book['id']}").json() == book


def test_update_missing_book_returns_404(client):
    response = client.put("/books/42", DUNE)
    assert response.status_code == 404
    assert client.get("/books").json() == []


def test_update_requires_json_content_type(client):
    book = create(client, DUNE)
    response = client.put(f"/books/{book['id']}", DUNE, content_type="text/plain")
    assert response.status_code == 415


# -- delete -------------------------------------------------------------------


def test_delete_book(client):
    book = create(client, DUNE)
    other = create(client, EMMA)

    response = client.delete(f"/books/{book['id']}")
    assert response.status_code == 204
    assert response.body == b""
    assert "content-type" not in response.headers

    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books").json() == [other]


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/42").status_code == 404


def test_delete_is_not_repeatable(client):
    book = create(client, DUNE)
    assert client.delete(f"/books/{book['id']}").status_code == 204
    assert client.delete(f"/books/{book['id']}").status_code == 404


# -- routing and errors -------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/book", "/books/1/reviews", "/healthz"])
def test_unknown_routes_return_json_404(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert "error" in response.json()


@pytest.mark.parametrize(
    "method, path, allowed",
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("PATCH", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_unsupported_methods_return_405(client, method, path, allowed):
    response = client.request(method, path)
    assert response.status_code == 405
    assert response.headers["allow"] == allowed
    assert "error" in response.json()


def test_unexpected_errors_return_json_500(client, repository, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(repository, "list_all", boom)
    response = client.get("/books")
    assert response.status_code == 500
    assert response.json() == {"error": "Internal server error"}
