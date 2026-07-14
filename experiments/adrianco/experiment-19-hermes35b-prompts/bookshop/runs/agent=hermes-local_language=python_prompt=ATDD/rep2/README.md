# Book API REST Service

A REST API for managing a book collection, built with Python, Flask, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- SQLite storage (embedded, no external DB server needed)
- 25 acceptance tests (ATDD)

## API Endpoints

| Method | Endpoint          | Description                     |
|--------|-------------------|---------------------------------|
| GET    | /health           | Health check                    |
| POST   | /books            | Create a new book               |
| GET    | /books            | List all books (?author= filter)|
| GET    | /books/{id}       | Get a single book by ID         |
| PUT    | /books/{id}       | Update a book                   |
| DELETE | /books/{id}       | Delete a book                   |

### Create Book - POST /books

**Request body:**
```json
{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}
```

**Validation errors (400 Bad Request):**
```json
{
    "error": "Title is required"
}
```

## Setup and Run

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
pip install flask requests
```

### Running the Server

```bash
python app.py
```

The server starts at `http://127.0.0.1:5001`.

If port 5001 is already in use, edit `app.py` and change the port in the last line.

### Running Tests

```bash
# Start the server first
python app.py

# In another terminal, run acceptance tests
python -m pytest test_app.py -v
```

The tests hit the live server at `http://127.0.0.1:5001` — this is true acceptance testing against the external API surface.

Each test starts with a clean, empty collection (enforced by the `conftest.py` fixture).

## Files

- `app.py` — Flask application with all API endpoints
- `test_app.py` — 25 acceptance tests (executable specification)
- `conftest.py` — Pytest fixture for test isolation (clears DB between tests)
- `books.db` — SQLite database (created automatically on server start)
- `README.md` — This file
