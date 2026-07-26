import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441013593",
    }
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
    assert isinstance(body["id"], int)
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441013593"


def test_create_book_optional_fields_default_to_none(client):
    resp = client.post("/books", json={"title": "Untitled", "author": "Anon"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload,expected_error",
    [
        ({"author": "Anon"}, "title is required"),
        ({"title": "Dune"}, "author is required"),
        ({"title": "  ", "author": "Anon"}, "title must be a non-empty string"),
        ({"title": "Dune", "author": "Anon", "year": "old"}, "year must be an integer"),
    ],
)
def test_create_book_validation_errors(client, payload, expected_error):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert expected_error in resp.get_json()["errors"]


def test_create_book_rejects_missing_body(client):
    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Neuromancer", author="William Gibson", year=1984)
    make_book(client, title="Children of Dune", year=1976)

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert len(all_books.get_json()) == 3

    filtered = client.get("/books?author=Frank Herbert")
    assert filtered.status_code == 200
    titles = [b["title"] for b in filtered.get_json()]
    assert titles == ["Dune", "Children of Dune"]

    empty = client.get("/books?author=Nobody")
    assert empty.get_json() == []


def test_get_single_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"

    assert client.get("/books/9999").status_code == 404


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.put(
        f"/books/{book_id}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == book_id
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969
    # isbn was omitted from the update, so it is cleared
    assert body["isbn"] is None

    # change is persisted
    assert client.get(f"/books/{book_id}").get_json()["title"] == "Dune Messiah"


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_update_validation_error(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "Only title"})
    assert resp.status_code == 400
    assert "author is required" in resp.get_json()["errors"]


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert resp.data == b""

    assert client.get(f"/books/{book_id}").status_code == 404
    # deleting twice is a 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not found"
