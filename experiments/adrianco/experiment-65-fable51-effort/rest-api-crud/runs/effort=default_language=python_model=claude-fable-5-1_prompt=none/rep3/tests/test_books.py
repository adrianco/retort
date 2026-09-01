"""Integration tests for the book collection API."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_and_body(client, sample_book):
    resp = client.post("/books", json=sample_book)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    for key, value in sample_book.items():
        assert body[key] == value


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 1999})
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert details["title"] == "is required"
    assert details["author"] == "is required"

    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["details"]


def test_create_rejects_bad_year_isbn_and_unknown_fields(client):
    resp = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": "2001", "isbn": "123", "colour": "red"},
    )
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert details["year"] == "must be an integer"
    assert "ISBN" in details["isbn"]
    assert "colour" in details["body"]


def test_create_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert "JSON" in resp.get_json()["error"]


def test_list_books_and_author_filter(client, sample_book):
    client.post("/books", json=sample_book)
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
    client.post("/books", json={"title": "Children of Dune", "author": "frank herbert"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == ["Release It!", "Dune", "Children of Dune"]

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Dune", "Children of Dune"]

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_single_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"]


def test_put_replaces_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "Release It! 2nd ed.", "author": "Michael T. Nygard"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Release It! 2nd ed."
    assert body["author"] == "Michael T. Nygard"
    # Full replacement: unspecified optional fields are cleared.
    assert body["year"] is None
    assert body["isbn"] is None


def test_put_validates_and_404s(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "Only title"})
    assert resp.status_code == 400
    assert resp.get_json()["details"]["author"] == "is required"

    resp = client.put("/books/12345", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_patch_updates_subset(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.patch(f"/books/{created['id']}", json={"year": 2020})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 2020
    assert body["title"] == sample_book["title"]

    resp = client.patch(f"/books/{created['id']}", json={})
    assert resp.status_code == 400


def test_delete_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json


def test_data_persists_across_app_instances(tmp_path, sample_book):
    from app import create_app

    db_path = str(tmp_path / "persist.db")
    first = create_app({"TESTING": True, "DATABASE": db_path})
    first.test_client().post("/books", json=sample_book)

    second = create_app({"TESTING": True, "DATABASE": db_path})
    resp = second.test_client().get("/books")
    assert len(resp.get_json()) == 1
