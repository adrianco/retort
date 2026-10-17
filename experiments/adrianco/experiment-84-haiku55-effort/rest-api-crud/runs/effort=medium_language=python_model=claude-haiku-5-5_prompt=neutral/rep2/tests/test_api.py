import json
import sqlite3
import urllib.error
import urllib.request

from books.app import BooksApp
from books.db import BookStore

from .conftest import VALID_BOOK


def create(client, **overrides):
    # ISBNs are unique, so helper-created books omit one unless asked for.
    body = {**VALID_BOOK, "isbn": None, **overrides}
    response = client.post("/books", body)
    assert response.status == 201, response.json
    return response.json


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status == 200
    assert response.json == {"status": "ok"}


def test_health_reports_unavailable_when_database_is_closed(store, client):
    store.close()
    response = client.get("/health")
    assert response.status == 503
    assert response.json == {"status": "unavailable"}


def test_create_book_returns_201_with_location(client):
    response = client.post("/books", VALID_BOOK)

    assert response.status == 201
    assert response.json["id"] == 1
    assert response.json["title"] == "Dune"
    assert response.json["author"] == "Frank Herbert"
    assert response.json["year"] == 1965
    assert response.json["isbn"] == "9780306406157"
    assert response.headers["Location"] == "/books/1"


def test_create_book_without_optional_fields(client):
    response = client.post("/books", {"title": "Untitled", "author": "Anon"})

    assert response.status == 201
    assert response.json["year"] is None
    assert response.json["isbn"] is None


def test_get_book_by_id(client):
    created = create(client)

    response = client.get(f"/books/{created['id']}")

    assert response.status == 200
    assert response.json == created


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status == 404
    assert response.json == {"error": "book not found"}


def test_list_books_returns_all_in_id_order(client):
    create(client, title="A")
    create(client, title="B")

    response = client.get("/books")

    assert response.status == 200
    assert [b["title"] for b in response.json] == ["A", "B"]


def test_list_books_filters_by_author_case_insensitively(client):
    create(client, title="Dune", author="Frank Herbert")
    create(client, title="Emma", author="Jane Austen")
    create(client, title="Children of Dune", author="Frank Herbert")

    response = client.get("/books", query="author=frank%20herbert")

    assert response.status == 200
    assert [b["title"] for b in response.json] == ["Dune", "Children of Dune"]


def test_list_with_empty_author_filter_returns_everything(client):
    create(client)
    create(client, title="Other", author="Someone")

    response = client.get("/books", query="author=")

    assert len(response.json) == 2


def test_update_replaces_book_fields(client):
    created = create(client)

    response = client.put(
        f"/books/{created['id']}",
        {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )

    assert response.status == 200
    assert response.json == {
        "id": created["id"],
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": None,
    }
    assert client.get(f"/books/{created['id']}").json == response.json


def test_update_missing_book_returns_404(client):
    response = client.put("/books/42", VALID_BOOK)
    assert response.status == 404


def test_update_validates_input(client):
    created = create(client)

    response = client.put(f"/books/{created['id']}", {"title": "", "author": "X"})

    assert response.status == 400
    assert "title" in response.json["details"]


def test_delete_book_returns_204_and_removes_it(client):
    created = create(client)

    response = client.delete(f"/books/{created['id']}")

    assert response.status == 204
    assert response.json is None
    assert client.get(f"/books/{created['id']}").status == 404


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/7").status == 404


def test_create_requires_title_and_author(client):
    response = client.post("/books", {"year": 2000})

    assert response.status == 400
    assert response.json["error"] == "validation failed"
    assert response.json["details"] == {
        "title": "is required",
        "author": "is required",
    }


def test_create_rejects_blank_title(client):
    response = client.post("/books", {"title": "   ", "author": "Someone"})

    assert response.status == 400
    assert response.json["details"] == {"title": "must be a non-empty string"}


def test_create_rejects_non_object_body(client):
    response = client.post("/books", ["not", "an", "object"])

    assert response.status == 400
    assert response.json["details"] == {"body": "must be a JSON object"}


def test_create_rejects_invalid_json(client):
    response = client.post("/books", raw=b"{not json")

    assert response.status == 400
    assert response.json == {"error": "request body must be valid JSON"}


def test_create_rejects_duplicate_isbn_in_any_formatting(client):
    create(client, isbn="0-306-40615-2")

    response = client.post("/books", {**VALID_BOOK, "title": "Other", "isbn": "0306406152"})

    assert response.status == 409
    assert response.json == {"error": "a book with this ISBN already exists"}


def test_update_to_another_books_isbn_conflicts(client):
    create(client, title="First", isbn="0-306-40615-2")
    second = create(client, title="Second", isbn="978-0-306-40615-7")

    response = client.put(
        f"/books/{second['id']}",
        {"title": "Second", "author": "Author", "isbn": "0-306-40615-2"},
    )

    assert response.status == 409


def test_unknown_route_returns_404(client):
    response = client.get("/nope")
    assert response.status == 404


def test_wrong_method_returns_405_with_allow_header(client):
    response = client.request("PATCH", "/books/1")
    assert response.status == 405
    assert response.headers["Allow"] == "GET, PUT, DELETE"

    response = client.request("DELETE", "/books")
    assert response.status == 405
    assert response.headers["Allow"] == "GET, POST"


def test_non_numeric_id_is_not_found(client):
    assert client.get("/books/abc").status == 404


def test_oversized_id_is_not_found_rather_than_crashing(client):
    assert client.get("/books/99999999999999999999999").status == 404


def test_books_are_persisted_in_sqlite_file(tmp_path):
    path = tmp_path / "books.db"

    store = BookStore(str(path))
    created = store.create({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None})
    store.close()

    reopened = BookStore(str(path))
    assert reopened.get(created["id"])["title"] == "Dune"
    reopened.close()

    raw = sqlite3.connect(path)
    assert raw.execute("SELECT title FROM books").fetchall() == [("Dune",)]
    raw.close()


def test_live_server_full_round_trip(live_server):
    def call(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            live_server + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"null")

    assert call("GET", "/health") == (200, {"status": "ok"})

    status, book = call("POST", "/books", VALID_BOOK)
    assert status == 201
    book_id = book["id"]

    assert call("GET", f"/books/{book_id}") == (200, book)
    assert call("GET", "/books?author=Frank%20Herbert")[0] == 200
    assert call("PUT", f"/books/{book_id}", {"title": "Dune", "author": "F. Herbert"})[0] == 200
    assert call("DELETE", f"/books/{book_id}")[0] == 204
    assert call("GET", f"/books/{book_id}")[0] == 404
    assert call("POST", "/books", {"title": ""})[0] == 400
