import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    with app.test_client() as client:
        yield client


def add_book(client, **overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    book.update(overrides)
    return client.post("/books", json=book)


def test_health_and_create_book(client):
    assert client.get("/health").json == {"status": "ok"}
    response = add_book(client)
    assert response.status_code == 201
    assert response.json["title"] == "Dune"
    assert response.json["id"] == 1


def test_list_filter_and_get_missing_book(client):
    add_book(client)
    add_book(client, title="Foundation", author="Isaac Asimov")
    assert len(client.get("/books?author=isaac%20asimov").json) == 1
    assert client.get("/books/999").status_code == 404


def test_update_and_delete_book(client):
    book_id = add_book(client).json["id"]
    updated = client.put(f"/books/{book_id}", json={"title": "Dune Messiah", "author": "Frank Herbert"})
    assert updated.status_code == 200
    assert updated.json["title"] == "Dune Messiah"
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_required_fields_are_validated(client):
    response = client.post("/books", json={"title": "Missing author"})
    assert response.status_code == 400
    assert "author" in response.json["error"]
