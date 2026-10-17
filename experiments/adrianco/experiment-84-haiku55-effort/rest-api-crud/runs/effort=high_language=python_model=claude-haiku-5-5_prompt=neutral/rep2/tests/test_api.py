import http.client
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest

from bookapi.server import MAX_BODY_BYTES


@dataclass
class Reply:
    status: int
    headers: object
    body: bytes

    def json(self):
        return json.loads(self.body) if self.body else None


def call(base_url, method, path, body=None, raw=None):
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base_url + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            return Reply(response.status, response.headers, response.read())
    except urllib.error.HTTPError as exc:
        return Reply(exc.code, exc.headers, exc.read())


DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def create(base_url, **overrides):
    reply = call(base_url, "POST", "/books", {**DUNE, **overrides})
    assert reply.status == 201, reply.body
    return reply.json()


def test_health_check(base_url):
    reply = call(base_url, "GET", "/health")
    assert reply.status == 200
    assert reply.json() == {"status": "ok"}


def test_health_reports_unavailable_when_database_is_closed(store, base_url):
    store.close()
    reply = call(base_url, "GET", "/health")
    assert reply.status == 503


def test_create_book_returns_201_with_location(base_url):
    reply = call(base_url, "POST", "/books", DUNE)
    book = reply.json()

    assert reply.status == 201
    assert reply.headers["Location"] == f"/books/{book['id']}"
    assert book == {"id": book["id"], **DUNE}


def test_create_book_without_optional_fields(base_url):
    book = call(base_url, "POST", "/books", {"title": "Emma", "author": "Jane Austen"}).json()
    assert book["year"] is None and book["isbn"] is None


def test_create_rejects_missing_title_and_author(base_url):
    reply = call(base_url, "POST", "/books", {"year": 1965})
    assert reply.status == 400
    assert reply.json()["error"] == "Validation failed"
    assert set(reply.json()["details"]) == {"title", "author"}


def test_create_rejects_invalid_json(base_url):
    reply = call(base_url, "POST", "/books", raw=b"{not json")
    assert reply.status == 400
    assert reply.json()["details"] == {"body": "must be valid JSON"}


def test_create_rejects_empty_body(base_url):
    reply = call(base_url, "POST", "/books")
    assert reply.status == 400


def test_get_book_by_id(base_url):
    created = create(base_url)
    reply = call(base_url, "GET", f"/books/{created['id']}")
    assert reply.status == 200
    assert reply.json() == created


def test_get_unknown_book_returns_404(base_url):
    assert call(base_url, "GET", "/books/9999").status == 404
    assert call(base_url, "GET", "/books/abc").status == 404
    assert call(base_url, "GET", "/books/99999999999999999999999").status == 404


def test_list_all_books(base_url):
    create(base_url, title="Dune")
    create(base_url, title="Emma", author="Jane Austen")
    reply = call(base_url, "GET", "/books")
    assert reply.status == 200
    assert [b["title"] for b in reply.json()] == ["Dune", "Emma"]


def test_list_filters_by_author(base_url):
    create(base_url, title="Dune")
    create(base_url, title="Emma", author="Jane Austen")
    books = call(base_url, "GET", "/books?author=jane%20austen").json()
    assert [b["title"] for b in books] == ["Emma"]
    assert call(base_url, "GET", "/books?author=Nobody").json() == []


def test_list_rejects_blank_author_filter(base_url):
    assert call(base_url, "GET", "/books?author=%20").status == 400


def test_put_replaces_book(base_url):
    created = create(base_url)
    reply = call(base_url, "PUT", f"/books/{created['id']}",
                 {"title": "Dune Messiah", "author": "Frank Herbert"})
    assert reply.status == 200
    assert reply.json() == {"id": created["id"], "title": "Dune Messiah",
                            "author": "Frank Herbert", "year": None, "isbn": None}
    assert call(base_url, "GET", f"/books/{created['id']}").json()["title"] == "Dune Messiah"


def test_put_validates_input(base_url):
    created = create(base_url)
    reply = call(base_url, "PUT", f"/books/{created['id']}", {"title": "Dune", "author": ""})
    assert reply.status == 400
    assert "author" in reply.json()["details"]


def test_put_unknown_book_returns_404(base_url):
    reply = call(base_url, "PUT", "/books/9999", DUNE)
    assert reply.status == 404


def test_delete_book(base_url):
    created = create(base_url)
    assert call(base_url, "DELETE", f"/books/{created['id']}").status == 204
    assert call(base_url, "GET", f"/books/{created['id']}").status == 404


def test_delete_unknown_book_returns_404(base_url):
    assert call(base_url, "DELETE", "/books/9999").status == 404


def test_unknown_route_returns_404_json(base_url):
    reply = call(base_url, "GET", "/nope")
    assert reply.status == 404
    assert reply.json() == {"error": "Not found"}


def test_wrong_method_returns_405_with_allow_header(base_url):
    reply = call(base_url, "PATCH", "/books")
    assert reply.status == 405
    assert reply.headers["Allow"] == "GET, POST"


def test_oversized_body_is_rejected_without_being_read(base_url):
    # Send only the headers: the server answers 413 and closes before the body arrives.
    connection = http.client.HTTPConnection(base_url.removeprefix("http://"))
    connection.putrequest("POST", "/books")
    connection.putheader("Content-Type", "application/json")
    connection.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 413
    connection.close()


def test_concurrent_creates_all_persist(base_url):
    with ThreadPoolExecutor(max_workers=8) as pool:
        replies = list(pool.map(
            lambda i: call(base_url, "POST", "/books", {"title": f"Book {i}", "author": "Anon"}),
            range(40),
        ))
    assert all(r.status == 201 for r in replies)
    ids = {r.json()["id"] for r in replies}
    assert len(ids) == 40
    assert len(call(base_url, "GET", "/books").json()) == 40
