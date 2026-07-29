import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    application = create_app({"TESTING": True, "DATABASE": str(tmp_path / "books.db")})
    return application.test_client()


def create_book(client, **overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}
    book.update(overrides)
    return client.post("/books", json=book)


def test_health_and_create_book(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    response = create_book(client)
    assert response.status_code == 201
    assert response.get_json()["title"] == "Dune"
    assert response.get_json()["id"] == 1


def test_validation_and_author_filter(client):
    assert client.post("/books", json={"title": "Missing author"}).status_code == 400
    create_book(client, author="Ursula Le Guin")
    create_book(client, title="The Left Hand of Darkness", author="Ursula Le Guin")
    response = client.get("/books?author=ursula")
    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_update_and_delete_book(client):
    book_id = create_book(client).get_json()["id"]
    updated = client.put(f"/books/{book_id}", json={"title": "Dune Messiah"})
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Dune Messiah"
    assert client.get(f"/books/{book_id}").status_code == 200
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
