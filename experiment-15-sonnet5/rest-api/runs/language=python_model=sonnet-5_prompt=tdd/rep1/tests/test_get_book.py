def test_get_book_by_id_returns_book(client):
    create_response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    )
    book_id = create_response.json()["id"]

    response = client.get(f"/books/{book_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Dune"


def test_get_book_missing_returns_404(client):
    response = client.get("/books/999")

    assert response.status_code == 404
