import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_id(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "Nobody"},
        {"title": "No Author"},
        {"title": "  ", "author": "Nobody"},
        {"title": "T", "author": "A", "year": "not-a-year"},
    ],
)
def test_create_book_validation_errors(client, payload):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["errors"]


def test_list_and_author_filter(client):
    make_book(client)
    make_book(client, title="Neuromancer", author="William Gibson", year=1984)

    assert len(client.get("/books").get_json()) == 2

    filtered = client.get("/books?author=William Gibson").get_json()
    assert [b["title"] for b in filtered] == ["Neuromancer"]

    assert client.get("/books?author=Nobody").get_json() == []


def test_get_single_book_and_404(client):
    book_id = make_book(client).get_json()["id"]
    assert client.get(f"/books/{book_id}").get_json()["title"] == "Dune"
    assert client.get("/books/9999").status_code == 404


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(
        f"/books/{book_id}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {
        "id": book_id,
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": None,
    }
    assert client.get(f"/books/{book_id}").get_json()["title"] == "Dune Messiah"


def test_update_missing_book_404_and_invalid_400(client):
    assert client.put("/books/9999", json={"title": "X", "author": "Y"}).status_code == 404
    book_id = make_book(client).get_json()["id"]
    assert client.put(f"/books/{book_id}", json={"author": "Y"}).status_code == 400


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404
