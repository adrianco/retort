def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


def test_create_book_returns_201_with_location(client):
    resp = client.post("/books", json={"title": "Neuromancer", "author": "William Gibson"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Neuromancer"
    assert body["author"] == "William Gibson"
    assert body["year"] is None
    assert body["isbn"] is None
    assert resp.headers["Location"] == "/books/1"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "title is required" in details
    assert "author is required" in details

    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400
    assert "title must be a non-empty string" in resp.get_json()["details"]


def test_create_rejects_bad_types_and_unknown_fields(client):
    resp = client.post("/books", json={
        "title": "T", "author": "A", "year": "1999", "isbn": "123", "colour": "red",
    })
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "year must be an integer" in details
    assert any(d.startswith("isbn must be") for d in details)
    assert "unknown field(s): colour" in details


def test_create_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert "JSON" in resp.get_json()["error"]


def test_isbn_is_normalised(client, book):
    assert book["isbn"] == "9780441013593"


def test_list_books_and_author_filter(client, book):
    client.post("/books", json={"title": "Children of Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == [
        "Dune", "Children of Dune", "Foundation"]

    resp = client.get("/books", query_string={"author": "frank herbert"})
    assert [b["title"] for b in resp.get_json()] == ["Dune", "Children of Dune"]

    resp = client.get("/books", query_string={"author": "Nobody"})
    assert resp.get_json() == []


def test_get_book(client, book):
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == book

    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "book not found"


def test_update_book(client, book):
    resp = client.put(f"/books/{book['id']}", json={"year": 1966, "isbn": None})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 1966
    assert body["isbn"] is None
    assert body["title"] == "Dune"  # untouched

    resp = client.put(f"/books/{book['id']}", json={"title": ""})
    assert resp.status_code == 400

    resp = client.put(f"/books/{book['id']}", json={})
    assert resp.status_code == 400
    assert "no updatable fields supplied" in resp.get_json()["details"]

    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client, book):
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert resp.data == b""

    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.delete(f"/books/{book['id']}").status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}


def test_data_persists_across_app_instances(tmp_path):
    from app import create_app

    path = str(tmp_path / "persist.db")
    c1 = create_app({"DATABASE": path}).test_client()
    c1.post("/books", json={"title": "A", "author": "B"})

    c2 = create_app({"DATABASE": path}).test_client()
    assert len(c2.get("/books").get_json()) == 1
