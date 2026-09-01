def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client, sample_book):
    resp = client.post("/books", json=sample_book)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    for key, value in sample_book.items():
        assert body[key] == value


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Validation failed"
    assert "title" in body["details"]
    assert "author" in body["details"]

    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["details"]


def test_create_book_rejects_bad_year_and_isbn(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "1999", "isbn": "abc"}
    )
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "year" in details
    assert "isbn" in details


def test_create_book_rejects_non_json(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_and_filter_by_author(client, sample_book):
    client.post("/books", json=sample_book)
    client.post("/books", json={"title": "Children of Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Neuromancer", "author": "William Gibson"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Frank%20Herbert")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Dune", "Children of Dune"]

    resp = client.get("/books?author=frank%20herbert")
    assert len(resp.get_json()) == 2

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Book not found"


def test_update_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "Dune (Deluxe)", "year": 2019})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Dune (Deluxe)"
    assert body["year"] == 2019
    assert body["author"] == sample_book["author"]

    resp = client.put(f"/books/{created['id']}", json={"author": ""})
    assert resp.status_code == 400

    resp = client.put(f"/books/{created['id']}", json={})
    assert resp.status_code == 400

    resp = client.put("/books/999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_book(client, sample_book):
    created = client.post("/books", json=sample_book).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Resource not found"
