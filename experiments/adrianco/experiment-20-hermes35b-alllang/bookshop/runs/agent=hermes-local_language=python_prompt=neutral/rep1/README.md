# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## API Endpoints

### Health Check
- GET /health - Returns 200 with {"status": "ok"}

### Books
- POST /books - Create a new book
- GET /books - List all books (optional query param ?author= to filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book

### Request/Response Format

All requests and responses use JSON. A book object has the following fields:

- id (integer) - auto-generated
- title (string, required)
- author (string, required)
- year (integer, optional)
- isbn (string, optional)
- created_at (datetime ISO 8601)
- updated_at (datetime ISO 8601)

Example POST request body:

  {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}

Example response:

  {"id": 1, "title": "1984", "author": "George Orwell", "year": 1949, ...}

## Setup and Run

### Requirements
- Python 3.11+
- Flask
- Flask-SQLAlchemy
- pytest (for testing)

### Installation

Install the dependencies:

  pip install flask flask-sqlalchemy pytest

### Run the Server

  python app.py

The server starts on http://0.0.0.0:5000 by default.

### Run Tests

  python -m pytest test_app.py -v

14 integration tests covering all endpoints, validation, and edge cases.

## Database

Data is stored in a local SQLite database file (books.db) created automatically on startup.

## API Usage Examples

Create a book:
  curl -X POST http://localhost:5000/books \
    -H "Content-Type: application/json" \
    -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

List all books:
  curl http://localhost:5000/books

List books by author:
  curl "http://localhost:5000/books?author=Frank"

Get a single book:
  curl http://localhost:5000/books/1

Update a book:
  curl -X PUT http://localhost:5000/books/1 \
    -H "Content-Type: application/json" \
    -d '{"year": 1966}'

Delete a book:
  curl -X DELETE http://localhost:5000/books/1
