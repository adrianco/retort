import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "t.db")).test_client()


B = {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"}


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_create_and_get(client):
    r = client.post("/books", json=B)
    assert r.status_code == 201
    assert client.get(f"/books/{r.get_json()['id']}").get_json()["title"] == "Dune"


def test_validation(client):
    assert client.post("/books", json={"author": "x"}).status_code == 400
    assert client.post("/books", json={"title": "x", "author": " "}).status_code == 400
    assert client.post("/books", json={**B, "year": "abc"}).status_code == 400
    assert client.post("/books", data="nope").status_code == 400


def test_list_filter(client):
    client.post("/books", json=B)
    client.post("/books", json={**B, "author": "Other"})
    assert len(client.get("/books").get_json()) == 2
    assert len(client.get("/books?author=Other").get_json()) == 1


def test_update_delete(client):
    i = client.post("/books", json=B).get_json()["id"]
    r = client.put(f"/books/{i}", json={**B, "title": "New"})
    assert r.get_json()["title"] == "New"
    assert client.put(f"/books/{i}", json={"title": ""}).status_code == 400
    assert client.delete(f"/books/{i}").status_code == 204
    assert client.get(f"/books/{i}").status_code == 404
    assert client.delete(f"/books/{i}").status_code == 404
    assert client.put("/books/99", json=B).status_code == 404
