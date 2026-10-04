import io
import json

import app as api


def call(method, path, payload=None, query=""):
    body = json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    result = {}

    def start_response(status, headers):
        result["status"] = int(status.split()[0])
        result["headers"] = dict(headers)

    response = b"".join(api.app(environ, start_response))
    result["body"] = json.loads(response) if response else None
    return result


def setup_function(function, tmp_path=None):
    # A file-backed database lets the app's per-request connections share state.
    import tempfile
    import os

    api.DATABASE = os.path.join(tempfile.gettempdir(), f"books-api-{function.__name__}.sqlite")
    if os.path.exists(api.DATABASE):
        os.unlink(api.DATABASE)


def test_health_and_create_and_fetch():
    assert call("GET", "/health")["status"] == 200
    created = call("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"})
    assert created["status"] == 201
    assert created["body"]["title"] == "Dune"
    assert call("GET", f"/books/{created['body']['id']}")["body"]["author"] == "Frank Herbert"


def test_list_author_filter_and_update():
    book = call("POST", "/books", {"title": "A", "author": "Author"})["body"]
    call("POST", "/books", {"title": "B", "author": "Other"})
    assert len(call("GET", "/books", query="author=Author")["body"]) == 1
    updated = call("PUT", f"/books/{book['id']}", {"title": "Changed", "author": "Author", "year": 2020})
    assert updated["status"] == 200
    assert updated["body"]["title"] == "Changed"


def test_validation_not_found_and_delete():
    assert call("POST", "/books", {"title": "Missing author"})["status"] == 400
    book = call("POST", "/books", {"title": "A", "author": "B"})["body"]
    assert call("DELETE", f"/books/{book['id']}")["status"] == 204
    assert call("GET", f"/books/{book['id']}")["status"] == 404
