# Book Collection API

A REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Features

- `POST   /books` — Create a new book
- `GET    /books` — List all books (supports `?author=` filter)
- `GET    /books/{id}` — Get a single book by ID
- `PUT    /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET    /health` — Health check

Data is persisted in a local SQLite database (`books.db`). Responses are JSON with
appropriate HTTP status codes. `title` and `author` are required and validated.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The service starts on http://127.0.0.1:8000. Interactive API docs are available at
http://127.0.0.1:8000/docs.

## Example requests

```bash
# Create a book
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# List all books
curl http://127.0.0.1:8000/books

# Filter by author
curl "http://127.0.0.1:8000/books?author=Frank%20Herbert"

# Get one book
curl http://127.0.0.1:8000/books/1

# Update a book
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# Delete a book
curl -X DELETE http://127.0.0.1:8000/books/1

# Health check
curl http://127.0.0.1:8000/health
```

## HTTP status codes

| Code | Meaning |
|------|---------|
| 200  | Successful GET / PUT |
| 201  | Book created |
| 204  | Book deleted |
| 404  | Book not found |
| 422  | Validation error (e.g. missing/blank title or author) |

## Tests

```bash
pytest
```

The test suite (`tests/test_books.py`) covers the health check, full CRUD lifecycle,
the author filter, validation failures, and 404 handling — each run against an
isolated temporary database.

## Project structure

```
app/
  __init__.py
  db.py        # SQLite connection + schema
  models.py    # Pydantic validation models
  main.py      # FastAPI app and routes
tests/
  test_books.py
requirements.txt
README.md
```
