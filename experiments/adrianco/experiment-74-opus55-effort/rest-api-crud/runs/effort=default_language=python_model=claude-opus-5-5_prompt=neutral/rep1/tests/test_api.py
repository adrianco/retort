import http.client
import json
import os
import threading

import pytest

os.environ["BOOKS_QUIET"] = "1"

from app import BookStore, ValidationError, make_server, validate_book  # noqa: E402

VALID = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


@pytest.fixture
def server(tmp_path):
    srv = make_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    srv.store.close()


@pytest.fixture
def request_(server):
    def do(method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        data = raw if raw is not None else (json.dumps(body) if body is not None else None)
        headers = {"Content-Type": "application/json"} if data is not None else {}
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        text = resp.read()
        conn.close()
        return resp.status, (json.loads(text) if text else None), resp
    return do


# --- integration tests over real HTTP ---------------------------------------

def test_health(request_):
    status, body, resp = request_("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "database": "ok"}
    assert resp.getheader("Content-Type") == "application/json"


def test_create_and_get_book(request_):
    status, created, _ = request_("POST", "/books", VALID)
    assert status == 201
    assert isinstance(created["id"], int)
    assert {k: created[k] for k in VALID} == VALID

    status, fetched, _ = request_("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_requires_title_and_author(request_):
    status, body, _ = request_("POST", "/books", {"year": 2000})
    assert status == 400
    assert set(body["details"]) >= {"title", "author"}

    status, body, _ = request_("POST", "/books", {"title": "   ", "author": "X"})
    assert status == 400
    assert "title" in body["details"]


def test_create_rejects_invalid_json(request_):
    status, body, _ = request_("POST", "/books", raw="{not json")
    assert status == 400
    assert body["details"]["body"] == "must be valid JSON"


def test_list_and_author_filter(request_):
    request_("POST", "/books", VALID)
    request_("POST", "/books", {"title": "Children of Dune", "author": "Frank Herbert"})
    request_("POST", "/books", {"title": "Emma", "author": "Jane Austen"})

    status, books, _ = request_("GET", "/books")
    assert status == 200
    assert len(books) == 3

    status, books, _ = request_("GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Children of Dune"]

    status, books, _ = request_("GET", "/books?author=nobody")
    assert status == 200 and books == []


def test_update_book(request_):
    _, created, _ = request_("POST", "/books", VALID)
    updated_payload = {"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966}
    status, updated, _ = request_("PUT", f"/books/{created['id']}", updated_payload)
    assert status == 200
    assert updated["title"] == "Dune (Revised)"
    assert updated["year"] == 1966
    assert updated["isbn"] is None

    status, body, _ = request_("PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 400

    status, _, _ = request_("PUT", "/books/9999", updated_payload)
    assert status == 404


def test_delete_book(request_):
    _, created, _ = request_("POST", "/books", VALID)
    status, body, _ = request_("DELETE", f"/books/{created['id']}")
    assert status == 204 and body is None

    status, _, _ = request_("GET", f"/books/{created['id']}")
    assert status == 404
    status, _, _ = request_("DELETE", f"/books/{created['id']}")
    assert status == 404


def test_not_found_and_method_not_allowed(request_):
    assert request_("GET", "/books/abc")[0] == 404
    assert request_("GET", "/nope")[0] == 404
    assert request_("PATCH", "/books")[0] == 405
    assert request_("POST", "/health")[0] == 405


def test_data_persists_across_restarts(tmp_path):
    db = str(tmp_path / "persist.db")
    store = BookStore(db)
    book = store.create(validate_book(VALID))
    store.close()

    store = BookStore(db)
    assert store.get(book["id"]) == book
    store.close()


# --- unit tests for validation ----------------------------------------------

@pytest.mark.parametrize(
    "payload, field",
    [
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": "123"}, "isbn"),
        ({"title": "T", "author": "A", "isbn": 12345}, "isbn"),
        ({"title": 5, "author": "A"}, "title"),
        ({"title": "T", "author": "A", "color": "red"}, "unknown_fields"),
    ],
)
def test_validation_errors(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_validation_accepts_minimal_and_isbn10():
    assert validate_book({"title": " T ", "author": "A"}) == {"title": "T", "author": "A"}
    assert validate_book({"title": "T", "author": "A", "isbn": "0-306-40615-X"})["isbn"] == "0-306-40615-X"


def test_validation_rejects_non_object():
    with pytest.raises(ValidationError):
        validate_book(["not", "a", "dict"])
