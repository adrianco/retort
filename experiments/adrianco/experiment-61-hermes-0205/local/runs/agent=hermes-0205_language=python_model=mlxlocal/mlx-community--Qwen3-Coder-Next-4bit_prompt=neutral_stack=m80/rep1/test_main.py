import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a temporary file-based database
import tempfile
import os


@pytest.fixture(scope="function")
def test_engine():
    """Create a test engine for each test using a fresh database"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    
    yield engine
    
    # Cleanup the temporary database file
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function", autouse=True)
def setup_test_db(test_engine):
    """Set up the test database before each test"""
    # Import database and patch it
    import database
    database.engine = test_engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create test tables using the patched engine
    from database import Base
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_engine):
    """Create test client with overridden database dependency"""
    # Import after test_engine fixture is set up
    import database
    from database import Base, Book as BookModel
    from main import app, get_db
    
    # Patch SessionLocal if not already patched
    if database.SessionLocal.kw.get('bind') != test_engine:
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    def override_get_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_book():
    """Test book data"""
    return {
        "title": "Test Book Title",
        "author": "Test Author",
        "year": 2024,
        "isbn": "978012345678"
    }


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "book-api"


def test_create_book(client, test_book):
    """Test creating a new book"""
    response = client.post("/books", json=test_book)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == test_book["title"]
    assert data["author"] == test_book["author"]
    assert data["year"] == test_book["year"]
    assert data["isbn"] == test_book["isbn"]
    assert "id" in data


def test_create_book_validation_error(client):
    """Test creating a book with validation errors"""
    # Missing required fields
    response = client.post("/books", json={"title": "Only Title"})
    assert response.status_code == 422
    
    # Invalid year
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 1400,  # Too early
        "isbn": "1234567890"
    })
    assert response.status_code == 422


def test_get_books_empty(client):
    """Test getting books when database is empty"""
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_books_with_author_filter(client, test_book):
    """Test filtering books by author"""
    # Create a book
    client.post("/books", json=test_book)
    
    # Create another book with different author
    client.post("/books", json={
        "title": "Another Book",
        "author": "Different Author",
        "year": 2023,
        "isbn": "978098765432"
    })
    
    # Filter by author
    response = client.get("/books?author=Test%20Author")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Test Author"


def test_get_book_by_id(client, test_book):
    """Test getting a single book by ID"""
    # Create a book
    create_response = client.post("/books", json=test_book)
    book_id = create_response.json()["id"]
    
    # Get the book
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_book["title"]
    assert data["author"] == test_book["author"]


def test_get_book_not_found(client):
    """Test getting a non-existent book"""
    response = client.get("/books/99999")
    assert response.status_code == 404


def test_update_book(client, test_book):
    """Test updating a book"""
    # Create a book
    create_response = client.post("/books", json=test_book)
    book_id = create_response.json()["id"]
    
    # Update the book
    update_data = {"title": "Updated Title", "year": 2025}
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["year"] == 2025
    # Author should remain unchanged
    assert data["author"] == test_book["author"]


def test_update_book_not_found(client):
    """Test updating a non-existent book"""
    update_data = {"title": "Updated Title"}
    response = client.put("/books/99999", json=update_data)
    assert response.status_code == 404


def test_delete_book(client, test_book):
    """Test deleting a book"""
    # Create a book
    create_response = client.post("/books", json=test_book)
    book_id = create_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    
    # Verify the book is deleted
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book"""
    response = client.delete("/books/99999")
    assert response.status_code == 404
