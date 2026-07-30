import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "books.db")})
    return app.test_client()


def new_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health_and_create_get_book(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    created = new_book(client)
    assert created.status_code == 201
    book = created.get_json()
    assert book["id"] == 1
    assert client.get("/books/1").get_json() == book


def test_list_filters_by_author(client):
    new_book(client)
    new_book(client, title="Foundation", author="Isaac Asimov")
    response = client.get("/books?author=Frank%20Herbert")
    assert response.status_code == 200
    assert [book["title"] for book in response.get_json()] == ["Dune"]


def test_update_delete_and_missing_book(client):
    book_id = new_book(client).get_json()["id"]
    updated = client.put(f"/books/{book_id}", json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Dune Messiah"
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_title_and_author_are_required(client):
    assert client.post("/books", json={"author": "Someone"}).status_code == 400
    assert client.post("/books", json={"title": "Something", "author": ""}).status_code == 400
