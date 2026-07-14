def test_delete_book_returns_204_and_removes_book(client):
    create_response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    )
    book_id = create_response.json()["id"]

    response = client.delete(f"/books/{book_id}")

    assert response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_book_missing_returns_404(client):
    response = client.delete("/books/999")

    assert response.status_code == 404
