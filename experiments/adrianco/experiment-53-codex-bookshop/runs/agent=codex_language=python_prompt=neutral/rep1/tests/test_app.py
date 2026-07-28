import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    application = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    with application.test_client() as test_client:
        yield test_client


def test_health_and_create_book(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    assert response.status_code == 201
    assert response.get_json()["id"] == 1


def test_list_can_filter_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "1984", "author": "George Orwell"})
    response = client.get("/books?author=orwell")
    assert response.status_code == 200
    assert [book["title"] for book in response.get_json()] == ["1984"]


def test_update_and_delete_book(client):
    created = client.post("/books", json={"title": "Old", "author": "Author"}).get_json()
    book_id = created["id"]
    assert client.put(f"/books/{book_id}", json={"title": "New"}).get_json()["title"] == "New"
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_required_fields_are_validated(client):
    response = client.post("/books", json={"title": "Missing author"})
    assert response.status_code == 400
    assert "author" in response.get_json()["error"]
