"""Integration tests for the REST endpoints, driven through the WSGI interface."""

import pytest


def create(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    payload.update(overrides)
    response = client.post("/books", json=payload)
    assert response.status_code == 201, response.body
    return response.json()


# -- health -----------------------------------------------------------------

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_health_reports_unavailable_when_database_is_down(client, store):
    store.close()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


# -- create -----------------------------------------------------------------

def test_create_book_returns_201_with_location(client, book_payload):
    response = client.post("/books", json=book_payload)
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], **book_payload}
    assert response.headers["location"] == f"/books/{body['id']}"
    assert response.headers["content-type"] == "application/json; charset=utf-8"


def test_create_book_with_only_required_fields(client):
    body = create(client, year=None, isbn=None)
    assert body["year"] is None and body["isbn"] is None
    minimal = client.post("/books", json={"title": "T", "author": "A"})
    assert minimal.status_code == 201
    assert minimal.json()["year"] is None


def test_create_trims_whitespace_and_keeps_unicode(client):
    body = create(client, title="  Der Prozess  ", author="Franz Kafka ")
    assert body["title"] == "Der Prozess"
    assert body["author"] == "Franz Kafka"
    assert create(client, title="Ficciones", author="Jorge Luis Borges")["author"] == "Jorge Luis Borges"


def test_ids_are_unique_and_increasing(client):
    ids = [create(client, title=f"Book {i}")["id"] for i in range(3)]
    assert ids == sorted(set(ids))


# -- validation -------------------------------------------------------------

@pytest.mark.parametrize("payload, field", [
    ({"author": "A"}, "title"),
    ({"title": "T"}, "author"),
    ({"title": "", "author": "A"}, "title"),
    ({"title": "T", "author": "   "}, "author"),
    ({"title": None, "author": "A"}, "title"),
    ({"title": 123, "author": "A"}, "title"),
    ({"title": "T", "author": ["A"]}, "author"),
    ({"title": "T" * 256, "author": "A"}, "title"),
    ({"title": "T", "author": "A", "year": "1999"}, "year"),
    ({"title": "T", "author": "A", "year": 19.99}, "year"),
    ({"title": "T", "author": "A", "year": True}, "year"),
    ({"title": "T", "author": "A", "year": 0}, "year"),
    ({"title": "T", "author": "A", "year": 10000}, "year"),
    ({"title": "T", "author": "A", "isbn": 9780441172719}, "isbn"),
    ({"title": "T", "author": "A", "isbn": "9" * 33}, "isbn"),
])
def test_create_rejects_invalid_payload(client, payload, field):
    response = client.post("/books", json=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "Validation failed"
    assert field in body["details"]
    assert client.get("/books").json() == []


def test_validation_reports_every_invalid_field(client):
    response = client.post("/books", json={"year": "x"})
    assert set(response.json()["details"]) == {"title", "author", "year"}


@pytest.mark.parametrize("raw", [b"", b"   ", b"{not json", b"\xff\xfe", b"null", b"[]", b'"text"', b"42"])
def test_create_rejects_malformed_or_non_object_body(client, raw):
    response = client.post("/books", raw_body=raw)
    assert response.status_code == 400
    assert "error" in response.json()


def test_create_rejects_oversized_body(client):
    response = client.post("/books", raw_body=b"x", headers={"CONTENT_LENGTH": str(10 * 1024 * 1024)})
    assert response.status_code == 413


@pytest.mark.parametrize("length", ["abc", "-5"])
def test_create_rejects_bad_content_length(client, length):
    response = client.post("/books", raw_body=b"{}", headers={"CONTENT_LENGTH": length})
    assert response.status_code == 400


# -- list and filter --------------------------------------------------------

def test_list_is_empty_initially(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_all_books_in_id_order(client):
    created = [create(client, title=t) for t in ("A", "B", "C")]
    assert client.get("/books").json() == created


def test_list_filters_by_author(client):
    orwell = [create(client, title="1984", author="George Orwell"),
              create(client, title="Animal Farm", author="George Orwell")]
    create(client, title="Dune", author="Frank Herbert")

    response = client.get("/books?author=George%20Orwell")
    assert response.status_code == 200
    assert response.json() == orwell
    assert client.get("/books?author=Nobody").json() == []


def test_author_filter_is_case_insensitive_and_exact(client):
    create(client, title="Émile", author="Émile Zola")
    create(client, title="1984", author="George Orwell")
    assert len(client.get("/books?author=george+orwell").json()) == 1
    assert len(client.get("/books?author=%C3%89MILE%20ZOLA").json()) == 1
    assert client.get("/books?author=Orwell").json() == []


def test_blank_author_filter_is_ignored(client):
    create(client, title="A")
    create(client, title="B")
    assert len(client.get("/books?author=").json()) == 2


def test_author_filter_is_safe_against_sql_injection(client):
    create(client)
    assert client.get("/books?author=%27%20OR%20%271%27%3D%271").json() == []


# -- get --------------------------------------------------------------------

def test_get_book(client):
    book = create(client)
    response = client.get(f"/books/{book['id']}")
    assert response.status_code == 200
    assert response.json() == book


@pytest.mark.parametrize("book_id", ["999", "0", "abc", "-1", "1.5", "99999999999999999999999"])
def test_get_unknown_or_invalid_id_is_404(client, book_id):
    create(client)
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404
    assert response.json() == {"error": "Book not found"}


def test_trailing_slash_is_accepted(client):
    book = create(client)
    assert client.get("/books/").status_code == 200
    assert client.get(f"/books/{book['id']}/").json() == book


# -- update -----------------------------------------------------------------

def test_update_book_replaces_fields(client):
    book = create(client)
    response = client.put(f"/books/{book['id']}",
                          json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "9780441172696"})
    assert response.status_code == 200
    expected = {"id": book["id"], "title": "Dune Messiah", "author": "Frank Herbert",
                "year": 1969, "isbn": "9780441172696"}
    assert response.json() == expected
    assert client.get(f"/books/{book['id']}").json() == expected


def test_update_omitted_optional_fields_are_cleared(client):
    book = create(client)
    updated = client.put(f"/books/{book['id']}", json={"title": "T", "author": "A"}).json()
    assert updated["year"] is None and updated["isbn"] is None


def test_update_only_touches_the_target_book(client):
    first, second = create(client, title="One"), create(client, title="Two")
    client.put(f"/books/{first['id']}", json={"title": "Changed", "author": "X"})
    assert client.get(f"/books/{second['id']}").json() == second


def test_update_validates_input_and_leaves_book_unchanged(client):
    book = create(client)
    response = client.put(f"/books/{book['id']}", json={"title": "", "author": "A"})
    assert response.status_code == 400
    assert "title" in response.json()["details"]
    assert client.get(f"/books/{book['id']}").json() == book


def test_update_unknown_book_is_404(client):
    response = client.put("/books/42", json={"title": "T", "author": "A"})
    assert response.status_code == 404


# -- delete -----------------------------------------------------------------

def test_delete_book(client):
    book = create(client)
    response = client.delete(f"/books/{book['id']}")
    assert response.status_code == 204
    assert response.body == b""
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books").json() == []


def test_delete_unknown_book_is_404(client):
    assert client.delete("/books/42").status_code == 404
    assert client.delete("/books/abc").status_code == 404


def test_deleted_ids_are_not_reused(client):
    first = create(client)
    client.delete(f"/books/{first['id']}")
    assert create(client)["id"] > first["id"]


# -- routing ----------------------------------------------------------------

@pytest.mark.parametrize("method, url, allow", [
    ("DELETE", "/books", "GET, POST"),
    ("PUT", "/books", "GET, POST"),
    ("POST", "/books/1", "GET, PUT, DELETE"),
    ("POST", "/health", "GET"),
])
def test_wrong_method_is_405_with_allow_header(client, method, url, allow):
    response = client.request(method, url)
    assert response.status_code == 405
    assert response.headers["allow"] == allow


@pytest.mark.parametrize("url", ["/", "/nope", "/books/1/extra", "/health/x"])
def test_unknown_route_is_404(client, url):
    response = client.get(url)
    assert response.status_code == 404
    assert response.json() == {"error": "Not found"}


def test_unexpected_error_is_500_json(client, store, monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise RuntimeError("kaput")

    monkeypatch.setattr(store, "list_books", boom)
    response = client.get("/books")
    assert response.status_code == 500
    assert response.json() == {"error": "Internal server error"}
    assert "kaput" not in response.body.decode()
