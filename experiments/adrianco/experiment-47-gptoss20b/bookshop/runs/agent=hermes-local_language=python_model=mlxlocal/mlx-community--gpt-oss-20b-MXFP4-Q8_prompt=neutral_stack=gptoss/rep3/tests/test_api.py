import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_and_get_book():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create
        payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "1234567890"}
        resp = await ac.post("/books", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "1984"
        book_id = data["id"]
        # get
        resp = await ac.get(f"/books/{book_id}")
        assert resp.status_code == 200
        assert resp.json()["author"] == "George Orwell"

@pytest.mark.asyncio
async def test_list_and_filter():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # add two books with same author
        await ac.post("/books", json={"title": "Book1", "author": "A", "year": 2000})
        await ac.post("/books", json={"title": "Book2", "author": "A", "year": 2001})
        await ac.post("/books", json={"title": "Book3", "author": "B", "year": 2002})
        # list all
        resp = await ac.get("/books")
        assert resp.status_code == 200
        all_books = resp.json()
        assert len(all_books) >= 3
        # filter by author A
        resp = await ac.get("/books", params={"author": "A"})
        assert resp.status_code == 200
        filtered = resp.json()
        assert all(b["author"] == "A" for b in filtered)
        assert len(filtered) >= 2

@pytest.mark.asyncio
async def test_validation_and_update_and_delete():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # missing title
        resp = await ac.post("/books", json={"author": "X"})
        assert resp.status_code == 422
        # create
        resp = await ac.post("/books", json={"title": "To Delete", "author": "Z"})
        book_id = resp.json()["id"]
        # update
        resp = await ac.put(f"/books/{book_id}", json={"title": "Updated", "author": "Z", "year": 2020})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        # delete
        resp = await ac.delete(f"/books/{book_id}")
        assert resp.status_code == 204
        # confirm deletion
        resp = await ac.get(f"/books/{book_id}")
        assert resp.status_code == 404
