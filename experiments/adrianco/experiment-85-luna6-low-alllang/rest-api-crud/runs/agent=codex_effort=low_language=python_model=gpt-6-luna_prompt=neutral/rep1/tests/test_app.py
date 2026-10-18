import json

import pytest

from app import BookStore, make_handler


@pytest.fixture
def api(tmp_path):
    store = BookStore(str(tmp_path / "test.sqlite3"))
    handler = make_handler(store)
    # The route method only uses the configured store and can run without a socket.
    return handler.handle_api


def request(api, method, path, body=None):
    return api(method, path, body)


def test_health_and_create_and_get_book(api):
    assert request(api, "GET", "/health") == (200, {"status": "ok"})
    status, book = request(api, "POST", "/books", {
        "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"
    })
    assert status == 201
    assert book["title"] == "Dune"
    assert book["id"] > 0
    assert request(api, "GET", f"/books/{book['id']}") == (200, book)


def test_author_filter_update_and_delete(api):
    _, one = request(api, "POST", "/books", {"title": "Dune", "author": "Frank Herbert"})
    request(api, "POST", "/books", {"title": "Foundation", "author": "Isaac Asimov"})
    assert request(api, "GET", "/books?author=frank%20herbert")[1] == [one]
    status, updated = request(api, "PUT", f"/books/{one['id']}", {
        "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969
    })
    assert status == 200
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969
    assert request(api, "DELETE", f"/books/{one['id']}")[0] == 204
    assert request(api, "GET", f"/books/{one['id']}")[0] == 404


def test_required_fields_and_missing_resources(api):
    assert request(api, "POST", "/books", {"title": "No author"})[0] == 400
    assert request(api, "POST", "/books", {"title": "  ", "author": "Someone"})[0] == 400
    assert request(api, "GET", "/books/999")[0] == 404
    assert request(api, "PUT", "/books/999", {"title": "Missing", "author": "Nobody"})[0] == 404
