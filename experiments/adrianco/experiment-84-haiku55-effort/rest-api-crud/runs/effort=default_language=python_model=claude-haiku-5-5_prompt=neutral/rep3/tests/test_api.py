import http.client
import json
import threading

import pytest

from bookapi import create_server


@pytest.fixture
def server():
    srv = create_server("127.0.0.1", 0, ":memory:")
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    srv.store.close()


@pytest.fixture
def request_json(server):
    host, port = server.server_address[:2]

    def send(method, path, body=None, raw_body=None):
        conn = http.client.HTTPConnection(host, port, timeout=5)
        headers = {}
        data = None
        if raw_body is not None:
            data = raw_body
            headers["Content-Type"] = "application/json"
        elif body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        payload = json.loads(raw) if raw else None
        return resp.status, payload, dict(resp.getheaders())

    return send


DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
NEUROMANCER = {"title": "Neuromancer", "author": "William Gibson", "year": 1984}


def test_health_reports_ok(request_json):
    status, body, _ = request_json("GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "database": "ok"}


def test_create_then_get_book(request_json):
    status, created, headers = request_json("POST", "/books", DUNE)
    assert status == 201
    assert created["id"] == 1
    assert created["title"] == "Dune"
    assert created["isbn"] == "9780441172719"
    assert headers["Location"] == "/books/1"

    status, fetched, _ = request_json("GET", "/books/1")
    assert status == 200
    assert fetched == created


def test_optional_fields_are_null_when_omitted(request_json):
    _, created, _ = request_json("POST", "/books", {"title": "T", "author": "A"})
    assert created["year"] is None
    assert created["isbn"] is None


def test_list_returns_all_books_and_filters_by_author(request_json):
    request_json("POST", "/books", DUNE)
    request_json("POST", "/books", NEUROMANCER)
    request_json("POST", "/books", {"title": "Dune Messiah", "author": "frank herbert"})

    status, everything, _ = request_json("GET", "/books")
    assert status == 200
    assert [b["id"] for b in everything] == [1, 2, 3]

    status, filtered, _ = request_json("GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in filtered] == ["Dune", "Dune Messiah"]

    _, empty_filter, _ = request_json("GET", "/books?author=")
    assert len(empty_filter) == 3


def test_update_replaces_book(request_json):
    request_json("POST", "/books", DUNE)
    status, updated, _ = request_json("PUT", "/books/1", {"title": "Dune (revised)", "author": "Frank Herbert"})
    assert status == 200
    assert updated == {"id": 1, "title": "Dune (revised)", "author": "Frank Herbert", "year": None, "isbn": None}
    assert request_json("GET", "/books/1")[1] == updated


def test_delete_removes_book(request_json):
    request_json("POST", "/books", DUNE)
    status, body, _ = request_json("DELETE", "/books/1")
    assert status == 204
    assert body is None
    assert request_json("GET", "/books/1")[0] == 404
    assert request_json("DELETE", "/books/1")[0] == 404


def test_missing_book_returns_404_for_get_put_delete(request_json):
    assert request_json("GET", "/books/99")[1]["error"] == "not_found"
    assert request_json("PUT", "/books/99", {"title": "T", "author": "A"})[0] == 404
    assert request_json("DELETE", "/books/99")[0] == 404


@pytest.mark.parametrize("raw_id", ["abc", "1.5", "-1", "99999999999999999999999"])
def test_non_numeric_or_out_of_range_ids_are_not_found(request_json, raw_id):
    assert request_json("GET", f"/books/{raw_id}")[0] == 404


def test_create_validation_errors_return_400_with_details(request_json):
    status, body, _ = request_json("POST", "/books", {"title": "", "year": "1965"})
    assert status == 400
    assert body["error"] == "validation_failed"
    assert body["details"] == {"title": "must not be blank", "author": "is required", "year": "must be an integer"}


def test_update_validates_input(request_json):
    request_json("POST", "/books", DUNE)
    status, body, _ = request_json("PUT", "/books/1", {"title": "Only title"})
    assert status == 400
    assert body["details"] == {"author": "is required"}
    # The stored book is unchanged after a rejected update.
    assert request_json("GET", "/books/1")[1]["title"] == "Dune"


def test_malformed_json_returns_400(request_json):
    status, body, _ = request_json("POST", "/books", raw_body="{not json")
    assert status == 400
    assert body["error"] == "invalid_json"


def test_missing_body_returns_400(request_json):
    status, body, _ = request_json("POST", "/books")
    assert status == 400
    assert body["error"] == "invalid_json"


def test_unknown_route_returns_404_json(request_json):
    status, body, _ = request_json("GET", "/authors")
    assert status == 404
    assert body["error"] == "not_found"


def test_wrong_method_returns_405_with_allow_header(request_json):
    status, body, headers = request_json("PATCH", "/books/1")
    assert status == 405
    assert body["error"] == "method_not_allowed"
    assert headers["Allow"] == "DELETE, GET, PUT"


def test_trailing_slash_is_accepted(request_json):
    request_json("POST", "/books", DUNE)
    assert request_json("GET", "/books/")[0] == 200
    assert request_json("GET", "/books/1/")[0] == 200
