import pytest
from httpx import AsyncClient
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_crud():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create
        payload = {"title": "Test Book", "author": "John Doe", "year": 2020, "isbn": "12345"}
        r = await ac.post("/books", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == payload["title"]
        book_id = data["id"]
        # get
        r = await ac.get(f"/books/{book_id}")
        assert r.status_code == 200
        assert r.json()["author"] == payload["author"]
        # update
        upd = {"title": "Updated"}
        r = await ac.put(f"/books/{book_id}", json=upd)
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"
        # list filter
        r = await ac.get("/books?author=John Doe")
        assert r.status_code == 200
        assert any(b["id"]==book_id for b in r.json())
        # delete
        r = await ac.delete(f"/books/{book_id}")
        assert r.status_code == 204
        # confirm deleted
        r = await ac.get(f"/books/{book_id}")
        assert r.status_code == 404
