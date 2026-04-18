import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base

TEST_DATABASE_URL = "sqlite:///./test_books.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book():
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["id"] is not None


def test_create_book_missing_required_fields():
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422


def test_create_book_missing_title():
    response = client.post("/books", json={"author": "Someone"})
    assert response.status_code == 422


def test_list_books():
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    response = client.get("/books")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_books_filter_by_author():
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["author"] == "Alice"


def test_get_book():
    create_response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = create_response.json()["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Dune"


def test_get_book_not_found():
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_update_book():
    create_response = client.post("/books", json={"title": "Old Title", "author": "Author"})
    book_id = create_response.json()["id"]
    response = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Author"


def test_update_book_not_found():
    response = client.put("/books/9999", json={"title": "X"})
    assert response.status_code == 404


def test_delete_book():
    create_response = client.post("/books", json={"title": "To Delete", "author": "Author"})
    book_id = create_response.json()["id"]
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404


def test_delete_book_not_found():
    response = client.delete("/books/9999")
    assert response.status_code == 404
