import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    return app.test_client()


def test_create_get_and_persist(client):
    data = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}
    response = client.post("/books", json=data)
    assert response.status_code == 201
    book = response.get_json()
    assert {key: book[key] for key in data} == data
    assert client.get(f"/books/{book['id']}").get_json() == book
    assert client.get("/books").get_json() == [book]


def test_filter_update_and_delete(client):
    book = client.post("/books", json={"title": "One", "author": "A"}).get_json()
    client.post("/books", json={"title": "Two", "author": "B"})
    assert client.get("/books?author=A").get_json() == [book]
    response = client.put(f"/books/{book['id']}", json={"title": "New", "author": "B", "year": 2000})
    assert response.status_code == 200
    assert response.get_json()["title"] == "New"
    assert client.get("/books?author=A").get_json() == []
    assert client.delete(f"/books/{book['id']}").status_code == 200
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_validation_and_missing_books(client):
    for data in ({}, {"title": " ", "author": "A"}, {"title": "T", "author": "A", "year": True}, {"title": "T", "author": "A", "isbn": 123}):
        assert client.post("/books", json=data).status_code == 400
    assert client.post("/books", data="bad", content_type="application/json").status_code == 400
    assert client.put("/books/999", json={"title": "T", "author": "A"}).status_code == 404
    assert client.delete("/books/999").status_code == 404
    book = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    assert client.put(f"/books/{book['id']}", json={"title": "T"}).status_code == 400
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_persistence_across_app_instances(tmp_path):
    database = str(tmp_path / "persistent.sqlite3")
    first = create_app({"TESTING": True, "DATABASE": database}).test_client()
    book = first.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).get_json()
    second = create_app({"TESTING": True, "DATABASE": database}).test_client()
    assert second.get(f"/books/{book['id']}").get_json() == book


def test_out_of_range_year_is_rejected(client):
    response = client.post("/books", json={"title": "T", "author": "A", "year": 2**63})
    assert response.status_code == 400
    assert response.is_json
