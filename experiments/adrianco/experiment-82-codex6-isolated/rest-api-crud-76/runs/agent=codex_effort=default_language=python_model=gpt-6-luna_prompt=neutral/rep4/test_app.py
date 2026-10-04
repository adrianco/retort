import io
import json

import app


def request(monkeypatch, tmp_path, method, path, payload=None):
    monkeypatch.setattr(app, "DATABASE", str(tmp_path / "test.sqlite3"))
    raw = json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = int(status.split()[0])

    body = b"".join(app.application(environ, start_response))
    return captured["status"], json.loads(body) if body else None


def test_create_list_and_author_filter(monkeypatch, tmp_path):
    status, book = request(monkeypatch, tmp_path, "POST", "/books", {
        "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"
    })
    assert status == 201
    assert book["id"] == 1
    assert request(monkeypatch, tmp_path, "GET", "/books")[1] == [book]
    assert request(monkeypatch, tmp_path, "GET", "/books?author=Nobody")[1] == []


def test_validation_and_missing_book(monkeypatch, tmp_path):
    assert request(monkeypatch, tmp_path, "POST", "/books", {"title": "No author"})[0] == 400
    assert request(monkeypatch, tmp_path, "GET", "/books/99")[0] == 404


def test_update_delete_and_health(monkeypatch, tmp_path):
    _, book = request(monkeypatch, tmp_path, "POST", "/books", {"title": "Old", "author": "A"})
    status, updated = request(monkeypatch, tmp_path, "PUT", f"/books/{book['id']}",
                              {"title": "New", "author": "B", "year": 2000})
    assert status == 200 and updated["title"] == "New"
    assert request(monkeypatch, tmp_path, "DELETE", f"/books/{book['id']}")[0] == 204
    assert request(monkeypatch, tmp_path, "GET", "/health") == (200, {"status": "ok"})
