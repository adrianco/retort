"""Integration tests: real HTTP requests against a live server backed by SQLite."""

import http.client

from book_api.server import MAX_BODY_BYTES

LE_GUIN = {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "year": 1969, "isbn": "9780441478125"}
HERBERT = {"title": "Dune", "author": "Frank Herbert", "year": 1965}


def create(api, payload):
    result = api.post("/books", json_body=payload)
    assert result.status == 201, result.body
    return result.body


def test_health_endpoint_reports_ok(api):
    result = api.get("/health")

    assert result.status == 200
    assert result.body == {"status": "ok"}


def test_health_endpoint_reports_unavailable_when_database_is_closed(api, repository):
    repository.close()

    result = api.get("/health")

    assert result.status == 503
    assert result.body == {"status": "unavailable"}


def test_create_book_returns_201_with_location_and_stored_representation(api):
    result = api.post("/books", json_body=LE_GUIN)

    assert result.status == 201
    assert result.headers["Content-Type"] == "application/json; charset=utf-8"
    assert result.headers["Location"] == f"/books/{result.body['id']}"
    assert result.body == {"id": result.body["id"], **LE_GUIN}


def test_create_book_without_title_or_author_returns_400_and_stores_nothing(api):
    result = api.post("/books", json_body={"year": 1969})

    assert result.status == 400
    assert result.body == {
        "error": "Validation failed",
        "details": {"title": "is required", "author": "is required"},
    }
    assert api.get("/books").body == []


def test_create_book_with_invalid_year_returns_400(api):
    result = api.post("/books", json_body={**HERBERT, "year": "nineteen sixty-five"})

    assert result.status == 400
    assert set(result.body["details"]) == {"year"}


def test_malformed_json_returns_400(api):
    result = api.post("/books", raw_body=b"{not json", headers={"Content-Type": "application/json"})

    assert result.status == 400
    assert result.body == {"error": "Request body must be valid JSON"}


def test_non_object_json_returns_400(api):
    result = api.post("/books", raw_body=b'["Dune", "Frank Herbert"]')

    assert result.status == 400
    assert result.body == {"error": "Request body must be a JSON object"}


def test_oversized_body_is_rejected_with_413_before_it_is_read(server):
    # Only the headers are sent. The server must refuse based on Content-Length alone.
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port)
    try:
        conn.putrequest("POST", "/books")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
        conn.endheaders()
        response = conn.getresponse()

        assert response.status == 413
    finally:
        conn.close()


def test_get_book_returns_book_or_404(api):
    created = create(api, HERBERT)

    assert api.get(f"/books/{created['id']}").body == created
    missing = api.get("/books/9999")
    assert missing.status == 404
    assert missing.body == {"error": "Book not found"}


def test_ids_that_cannot_exist_are_not_found(api):
    for path in ("/books/abc", "/books/-1", "/books/0", "/books/99999999999999999999999"):
        assert api.get(path).status == 404, path


def test_list_books_returns_all_books_and_filters_by_author(api):
    herbert = create(api, HERBERT)
    le_guin = create(api, LE_GUIN)
    herbert_again = create(api, {**HERBERT, "title": "Dune Messiah"})

    assert api.get("/books").body == [herbert, le_guin, herbert_again]

    filtered = api.get("/books?author=frank%20herbert")
    assert filtered.status == 200
    assert filtered.body == [herbert, herbert_again]


def test_blank_author_filter_returns_every_book(api):
    created = create(api, HERBERT)

    assert api.get("/books?author=").body == [created]


def test_update_replaces_every_field(api):
    created = create(api, LE_GUIN)
    replacement = {"title": "Dune", "author": "Frank Herbert"}

    result = api.put(f"/books/{created['id']}", json_body=replacement)

    assert result.status == 200
    assert result.body == {"id": created["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}
    assert api.get(f"/books/{created['id']}").body == result.body


def test_update_requires_title_and_author_and_leaves_book_unchanged(api):
    created = create(api, HERBERT)

    result = api.put(f"/books/{created['id']}", json_body={"title": "Renamed"})

    assert result.status == 400
    assert result.body["details"] == {"author": "is required"}
    assert api.get(f"/books/{created['id']}").body == created


def test_update_missing_book_returns_404(api):
    result = api.put("/books/9999", json_body=HERBERT)

    assert result.status == 404


def test_delete_book_returns_204_then_404(api):
    created = create(api, HERBERT)
    path = f"/books/{created['id']}"

    deleted = api.delete(path)
    assert deleted.status == 204
    assert deleted.body is None

    assert api.get(path).status == 404
    assert api.delete(path).status == 404


def test_unknown_route_returns_json_404(api):
    result = api.get("/authors")

    assert result.status == 404
    assert result.body == {"error": "Route not found"}


def test_wrong_method_returns_405_with_allow_header(api):
    collection = api.request("PATCH", "/books")
    assert collection.status == 405
    assert collection.headers["Allow"] == "GET, POST"

    item = api.request("PATCH", "/books/1")
    assert item.status == 405
    assert item.headers["Allow"] == "DELETE, GET, PUT"


def test_unexpected_errors_return_generic_500(api, repository, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(repository, "list_books", broken)

    result = api.get("/books")

    assert result.status == 500
    assert result.body == {"error": "Internal server error"}
