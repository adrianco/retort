import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server, validate_book, ValidationError


@pytest.fixture()
def base_url(tmp_path):
    server, store = create_server("127.0.0.1", 0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    store.close()


def call(base_url, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_health(base_url):
    assert call(base_url, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get_book(base_url):
    status, created = call(base_url, "POST", "/books", BOOK)
    assert status == 201
    assert created["id"] == 1
    assert {k: created[k] for k in BOOK} == BOOK

    status, fetched = call(base_url, "GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_validation_errors(base_url):
    status, body = call(base_url, "POST", "/books", {"author": "Nobody"})
    assert status == 400
    assert "title" in body["details"]

    status, body = call(base_url, "POST", "/books", {"title": "  ", "author": "X"})
    assert status == 400
    assert "title" in body["details"]

    status, body = call(base_url, "POST", "/books", {"title": "T", "author": "A", "year": "1999"})
    assert status == 400
    assert "year" in body["details"]

    status, body = call(base_url, "POST", "/books", {"title": "T", "author": "A", "isbn": "abc"})
    assert status == 400
    assert "isbn" in body["details"]


def test_malformed_json(base_url):
    req = urllib.request.Request(base_url + "/books", data=b"{not json", method="POST",
                                 headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400


def test_list_and_filter_by_author(base_url):
    call(base_url, "POST", "/books", BOOK)
    call(base_url, "POST", "/books", {"title": "Children of Dune", "author": "Frank Herbert"})
    call(base_url, "POST", "/books", {"title": "Neuromancer", "author": "William Gibson"})

    status, all_books = call(base_url, "GET", "/books")
    assert status == 200
    assert len(all_books) == 3

    status, herbert = call(base_url, "GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in herbert] == ["Dune", "Children of Dune"]

    status, none = call(base_url, "GET", "/books?author=Unknown")
    assert (status, none) == (200, [])


def test_update_book(base_url):
    _, created = call(base_url, "POST", "/books", BOOK)
    updated_payload = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, updated = call(base_url, "PUT", f"/books/{created['id']}", updated_payload)
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert updated["isbn"] is None

    status, body = call(base_url, "PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 400

    status, _ = call(base_url, "PUT", "/books/999", updated_payload)
    assert status == 404


def test_delete_book(base_url):
    _, created = call(base_url, "POST", "/books", BOOK)
    status, body = call(base_url, "DELETE", f"/books/{created['id']}")
    assert (status, body) == (204, None)
    status, _ = call(base_url, "GET", f"/books/{created['id']}")
    assert status == 404
    status, _ = call(base_url, "DELETE", f"/books/{created['id']}")
    assert status == 404


def test_unknown_routes_and_methods(base_url):
    assert call(base_url, "GET", "/nope")[0] == 404
    assert call(base_url, "DELETE", "/books")[0] == 405
    assert call(base_url, "POST", "/books/1")[0] == 405


def test_validate_book_unit():
    clean = validate_book({"title": " A ", "author": "B", "isbn": "0-306-40615-2"})
    assert clean == {"title": "A", "author": "B", "year": None, "isbn": "0-306-40615-2"}
    with pytest.raises(ValidationError) as exc:
        validate_book({"title": "A", "author": "B", "year": True})
    assert "year" in exc.value.errors
    with pytest.raises(ValidationError):
        validate_book(["not", "a", "dict"])
