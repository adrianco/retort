import pytest

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "9780141439587"}
PERSUASION = {"title": "Persuasion", "author": "Jane Austen", "year": 1817, "isbn": None}


def create(client, book):
    response = client.post("/books", book)
    assert response.status == 201
    return response.json()


# --- health ---------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_reports_unavailable_database(app, client):
    app.store.close()
    response = client.get("/health")
    assert response.status == 503
    assert response.json() == {"error": "Database unavailable"}


# --- create ---------------------------------------------------------------


def test_create_book(client):
    response = client.post("/books", DUNE)
    assert response.status == 201
    assert response.headers["content-type"] == "application/json"
    book = response.json()
    assert book == {"id": book["id"], **DUNE}
    assert isinstance(book["id"], int)
    assert response.headers["location"] == f"/books/{book['id']}"
    assert client.get(response.headers["location"]).json() == book


def test_create_book_with_only_required_fields(client):
    response = client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 201
    book = response.json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_trims_whitespace_and_ignores_unknown_fields(client):
    response = client.post(
        "/books",
        {"id": 999, "title": "  Dune ", "author": " Frank Herbert", "isbn": "  ", "rating": 5},
    )
    assert response.status == 201
    book = response.json()
    assert book == {
        "id": book["id"],
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }
    assert book["id"] != 999


def test_create_preserves_unicode(client):
    book = create(client, {"title": "Война и мир", "author": "Лев Толстой"})
    fetched = client.get(f"/books/{book['id']}").json()
    assert fetched["title"] == "Война и мир"
    assert client.get("/books?author=Лев%20Толстой").json() == [fetched]


@pytest.mark.parametrize(
    "payload, invalid_fields",
    [
        ({}, {"title", "author"}),
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune"}, {"author"}),
        ({"title": None, "author": "Frank Herbert"}, {"title"}),
        ({"title": "", "author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune", "author": "   "}, {"author"}),
        ({"title": 42, "author": ["Frank Herbert"]}, {"title", "author"}),
        ({"title": "\ud800", "author": "Frank Herbert"}, {"title"}),
        ({**DUNE, "year": "1965"}, {"year"}),
        ({**DUNE, "year": 1965.5}, {"year"}),
        ({**DUNE, "year": True}, {"year"}),
        ({**DUNE, "year": 10**30}, {"year"}),
        ({**DUNE, "isbn": 9780441172719}, {"isbn"}),
        ({"year": "x", "isbn": 1}, {"title", "author", "year", "isbn"}),
    ],
)
def test_create_rejects_invalid_fields(client, payload, invalid_fields):
    response = client.post("/books", payload)
    assert response.status == 400
    body = response.json()
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == invalid_fields
    assert client.get("/books").json() == []


@pytest.mark.parametrize("body", [b"", b"{not json", b"\xff\xfe\xfd", b"[" * 100_000])
def test_create_rejects_malformed_json(client, body):
    response = client.post("/books", body=body)
    assert response.status == 400
    assert response.json() == {"error": "Request body must be valid JSON"}


@pytest.mark.parametrize("body", [b"[]", b'"Dune"', b"null", b"1"])
def test_create_rejects_non_object_json(client, body):
    response = client.post("/books", body=body)
    assert response.status == 400
    assert response.json()["details"] == {"body": "request body must be a JSON object"}


def test_create_rejects_oversized_body(client):
    response = client.post("/books", body=b" " * (1024 * 1024 + 1))
    assert response.status == 413


# --- list -----------------------------------------------------------------


def test_list_books_empty(client):
    response = client.get("/books")
    assert response.status == 200
    assert response.json() == []


def test_list_books_returns_all_in_creation_order(client):
    created = [create(client, book) for book in (DUNE, EMMA, PERSUASION)]
    response = client.get("/books")
    assert response.status == 200
    assert response.json() == created


def test_list_books_filters_by_author(client):
    create(client, DUNE)
    emma = create(client, EMMA)
    persuasion = create(client, PERSUASION)

    response = client.get("/books?author=Jane%20Austen")
    assert response.status == 200
    assert response.json() == [emma, persuasion]

    assert client.get("/books?author=Jane+Austen").json() == [emma, persuasion]
    assert client.get("/books?author=Nobody").json() == []
    # The filter is an exact match, not a substring search.
    assert client.get("/books?author=Jane").json() == []


def test_list_books_blank_author_filter_returns_all(client):
    created = [create(client, DUNE), create(client, EMMA)]
    assert client.get("/books?author=").json() == created


def test_author_filter_is_not_sql_injectable(client):
    create(client, DUNE)
    assert client.get("/books?author=x'%20OR%20'1'='1").json() == []


# --- get ------------------------------------------------------------------


def test_get_book(client):
    book = create(client, DUNE)
    response = client.get(f"/books/{book['id']}")
    assert response.status == 200
    assert response.json() == book


@pytest.mark.parametrize("book_id", ["1", "0", "99999999999999999999999", "9" * 5000])
def test_get_missing_book(client, book_id):
    response = client.get(f"/books/{book_id}")
    assert response.status == 404
    assert "not found" in response.json()["error"]


@pytest.mark.parametrize("path", ["/", "/nope", "/books/abc", "/books/-1", "/books/1/extra"])
def test_unknown_paths(client, path):
    response = client.get(path)
    assert response.status == 404
    assert response.json() == {"error": "Not found"}


# --- update ---------------------------------------------------------------


def test_update_book(client):
    book = create(client, DUNE)
    changes = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "9780441172696"}

    response = client.put(f"/books/{book['id']}", changes)
    assert response.status == 200
    assert response.json() == {"id": book["id"], **changes}
    assert client.get(f"/books/{book['id']}").json() == {"id": book["id"], **changes}


def test_update_replaces_the_whole_book(client):
    book = create(client, DUNE)
    response = client.put(f"/books/{book['id']}", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 200
    assert response.json()["year"] is None
    assert response.json()["isbn"] is None


def test_update_does_not_touch_other_books(client):
    dune = create(client, DUNE)
    emma = create(client, EMMA)
    client.put(f"/books/{dune['id']}", PERSUASION)
    assert client.get(f"/books/{emma['id']}").json() == emma


def test_update_rejects_invalid_book(client):
    book = create(client, DUNE)
    response = client.put(f"/books/{book['id']}", {"title": "", "year": 1969})
    assert response.status == 400
    assert set(response.json()["details"]) == {"title", "author"}
    assert client.get(f"/books/{book['id']}").json() == book


def test_update_missing_book(client):
    response = client.put("/books/1", DUNE)
    assert response.status == 404
    assert client.get("/books").json() == []


# --- delete ---------------------------------------------------------------


def test_delete_book(client):
    dune = create(client, DUNE)
    emma = create(client, EMMA)

    response = client.delete(f"/books/{dune['id']}")
    assert response.status == 204
    assert response.body == b""

    assert client.get(f"/books/{dune['id']}").status == 404
    assert client.get("/books").json() == [emma]


def test_delete_missing_book(client):
    assert client.delete("/books/1").status == 404


def test_deleted_ids_are_not_reused(client):
    first = create(client, DUNE)
    client.delete(f"/books/{first['id']}")
    second = create(client, EMMA)
    assert second["id"] != first["id"]


# --- routing --------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path, allowed",
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_method_not_allowed(client, method, path, allowed):
    response = client.request(method, path)
    assert response.status == 405
    assert response.headers["allow"] == allowed
    assert response.json() == {"error": "Method not allowed"}


def test_head_returns_get_headers_without_a_body(client):
    create(client, DUNE)
    for path in ("/health", "/books", "/books/1"):
        get = client.get(path)
        head = client.request("HEAD", path)
        assert head.status == 200
        assert head.body == b""
        assert head.headers == get.headers
    assert client.request("HEAD", "/books/2").status == 404


def test_trailing_slash_is_accepted(client):
    book = create(client, DUNE)
    assert client.get("/books/").json() == [book]
    assert client.get(f"/books/{book['id']}/").json() == book


def test_unexpected_errors_become_json_500(app, client):
    app.store.close()
    response = client.get("/books")
    assert response.status == 500
    assert response.json() == {"error": "Internal server error"}
