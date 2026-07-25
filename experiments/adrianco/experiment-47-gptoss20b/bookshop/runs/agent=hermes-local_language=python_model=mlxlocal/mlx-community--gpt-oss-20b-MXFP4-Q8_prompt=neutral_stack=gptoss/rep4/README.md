# Book Collection API

A small REST API for managing a collection of books.  It is implemented with **FastAPI** and **SQLAlchemy** using an SQLite database.

## Requirements
- Python 3.11+ (tested on 3.11.6)
- `pip install -r requirements.txt`

## Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create the database (tables are created automatically on start)
# Run the API
uvicorn main:app --reload
```

The service will be available on `http://localhost:8000`.

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST   | /books | Create a new book (title, author, year, isbn) |
| GET    | /books | List all books (optional `?author=` filter) |
| GET    | /books/{id} | Retrieve a book by ID |
| PUT    | /books/{id} | Update a book (partial updates allowed) |
| DELETE | /books/{id} | Delete a book |
| GET    | /health | Health‑check endpoint |

All responses are JSON.  Validation errors return `422`.

## Running Tests
```bash
pytest
```

The tests use `fastapi.testclient` and a temporary SQLite database.
