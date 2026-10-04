import io
import json

import pytest

from app import create_app

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


class Response:
    def __init__(self, status, headers, body):
        self.status_code = int(status.split()[0])
        self.headers = dict(headers)
        self.body = body

    def get_json(self):
        return json.loads(self.body)


class Client:
    """Minimal in-process client that calls the WSGI app directly."""

    def __init__(self, app):
        self.app = app

    def request(self, method, url, json_body=None, data=None):
        path, _, query = url.partition("?")
        if json_body is not None:
            data = json.dumps(json_body)
        body = (data or "").encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query.replace(" ", "%20"),
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}

        def start_response(status, headers):
            captured.update(status=status, headers=headers)

        payload = b"".join(self.app(environ, start_response))
        return Response(captured["status"], captured["headers"], payload)

    def get(self, url):
        return self.request("GET", url)

    def post(self, url, json=None, data=None, content_type=None):
        return self.request("POST", url, json, data)

    def put(self, url, json=None):
        return self.request("PUT", url, json)

    def delete(self, url):
        return self.request("DELETE", url)


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "test.db")))


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post("/books", json=BOOK)
    assert resp.status_code == 201
    created = resp.get_json()
    assert created == {"id": created["id"], **BOOK}
    assert resp.headers["Location"] == f"/books/{created['id']}"

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_create_with_only_required_fields(client):
    resp = client.post("/books", json={"title": "T", "author": "A"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None and body["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "A"},
        {"title": "T"},
        {"title": "  ", "author": "A"},
        {"title": "T", "author": 5},
        {"title": "T", "author": "A", "year": "1965"},
        {"title": "T", "author": "A", "year": True},
        {"title": "T", "author": "A", "isbn": 123},
        ["not", "an", "object"],
    ],
)
def test_create_validation_errors(client, payload):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "validation failed"
    assert body["details"]


def test_create_rejects_malformed_json(client):
    resp = client.post("/books", data="{nope", content_type="application/json")
    assert resp.status_code == 400


def test_duplicate_isbn_conflict(client):
    assert client.post("/books", json=BOOK).status_code == 201
    assert client.post("/books", json=BOOK).status_code == 409


def test_list_books_and_author_filter(client):
    client.post("/books", json=BOOK)
    client.post("/books", json={"title": "Emma", "author": "Jane Austen", "year": 1815})
    client.post("/books", json={"title": "Persuasion", "author": "Jane Austen"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == ["Dune", "Emma", "Persuasion"]

    resp = client.get("/books?author=Jane Austen")
    assert [b["title"] for b in resp.get_json()] == ["Emma", "Persuasion"]

    assert client.get("/books?author=Nobody").get_json() == []


def test_update_book(client):
    book_id = client.post("/books", json=BOOK).get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={**BOOK, "title": "Dune Messiah", "year": 1969})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune Messiah"
    assert client.get(f"/books/{book_id}").get_json()["year"] == 1969

    assert client.put(f"/books/{book_id}", json={"title": "No author"}).status_code == 400
    assert client.put("/books/9999", json=BOOK).status_code == 404


def test_delete_book(client):
    book_id = client.post("/books", json=BOOK).get_json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_not_found_is_json(client):
    resp = client.get("/books/12345")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "book not found"}

    resp = client.get("/nope")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_method_not_allowed(client):
    resp = client.delete("/books")
    assert resp.status_code == 405
    assert "error" in resp.get_json()


def test_data_persists_across_app_instances(tmp_path):
    db_path = str(tmp_path / "persist.db")
    book_id = Client(create_app(db_path)).post("/books", json=BOOK).get_json()["id"]
    assert Client(create_app(db_path)).get(f"/books/{book_id}").get_json()["title"] == "Dune"
