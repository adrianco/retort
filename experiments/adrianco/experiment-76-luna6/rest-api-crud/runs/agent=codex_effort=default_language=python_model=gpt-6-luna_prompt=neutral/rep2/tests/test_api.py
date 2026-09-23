import io
import json

from app import create_app


def request(app, method, path, data=None):
    body = json.dumps(data).encode() if data is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    result = {}
    payload = b"".join(app(environ, lambda status, headers: result.update(status=status, headers=dict(headers))))
    result["body"] = json.loads(payload) if payload else None
    return result


def test_create_list_filter_and_read(tmp_path):
    app = create_app(tmp_path / "books.db")
    first = request(app, "POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"})
    second = request(app, "POST", "/books", {"title": "Children of Dune", "author": "Frank Herbert"})
    request(app, "POST", "/books", {"title": "Foundation", "author": "Isaac Asimov"})
    assert first["status"].startswith("201")
    assert first["body"]["id"] == 1
    assert request(app, "GET", "/books")["body"] == [first["body"], second["body"], {"id": 3, "title": "Foundation", "author": "Isaac Asimov", "year": None, "isbn": None}]
    assert len(request(app, "GET", "/books?author=Frank%20Herbert")["body"]) == 2
    assert request(app, "GET", "/books/1")["body"]["title"] == "Dune"


def test_update_delete_and_missing_book(tmp_path):
    app = create_app(tmp_path / "books.db")
    created = request(app, "POST", "/books", {"title": "Old", "author": "A"})["body"]
    updated = request(app, "PUT", f"/books/{created['id']}", {"title": "New", "author": "B", "year": 2024})
    assert updated["status"].startswith("200")
    assert updated["body"]["title"] == "New"
    assert request(app, "DELETE", f"/books/{created['id']}")["status"].startswith("204")
    assert request(app, "GET", f"/books/{created['id']}")["status"].startswith("404")


def test_validation_and_health(tmp_path):
    app = create_app(tmp_path / "books.db")
    invalid = request(app, "POST", "/books", {"title": "No author"})
    assert invalid["status"].startswith("400")
    assert "author" in invalid["body"]["error"]
    assert request(app, "GET", "/health")["body"] == {"status": "ok"}
