import io
import json

import pytest

from app import BookAPI


@pytest.fixture
def api(tmp_path):
    return BookAPI(str(tmp_path / "test.db"))


def request(api, method, path, data=None):
    path, _, query = path.partition("?")
    body = b"" if data is None else json.dumps(data).encode()
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = int(status.split()[0])
        captured["headers"] = headers

    result = b"".join(api(environ, start_response))
    return captured["status"], json.loads(result) if result else None


def test_create_get_filter_and_update(api):
    status, book = request(api, "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert status == 201
    assert book["id"] == 1
    assert request(api, "GET", "/books/1") == (200, book)
    assert request(api, "GET", "/books?author=Other") == (200, [])
    status, updated = request(api, "PUT", "/books/1", {"title": "Dune Messiah", "author": "Frank Herbert"})
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] is None


def test_validation_and_missing_book(api):
    assert request(api, "POST", "/books", {"title": "No author"})[0] == 400
    assert request(api, "GET", "/books/999")[0] == 404
    assert request(api, "PUT", "/books/999", {"title": "X", "author": "Y"})[0] == 404


def test_delete_list_and_health(api):
    _, book = request(api, "POST", "/books", {"title": "Book", "author": "Writer", "isbn": "123"})
    assert request(api, "GET", "/health") == (200, {"status": "ok"})
    assert request(api, "DELETE", f"/books/{book['id']}") == (204, None)
    assert request(api, "GET", "/books") == (200, [])
    assert request(api, "DELETE", f"/books/{book['id']}")[0] == 404
