# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and
**SQLite**.

## Features

- `POST /books` — Create a new book (`title`, `author`, `year`, `isbn`)
- `GET /books` — List all books, with an optional `?author=` filter
- `GET /books/{id}` — Get a single book by id
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

Data is stored in a local SQLite database (`books.db`). Responses are JSON with
appropriate HTTP status codes. `title` and `author` are required and validated.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The service listens on <http://127.0.0.1:8000>. Interactive API docs are
available at <http://127.0.0.1:8000/docs>.

## Example requests

```bash
# Create a book
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "12345"}'

# List books filtered by author
curl "http://127.0.0.1:8000/books?author=Frank%20Herbert"

# Get a book by id
curl http://127.0.0.1:8000/books/1

# Update a book
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete a book
curl -X DELETE http://127.0.0.1:8000/books/1

# Health check
curl http://127.0.0.1:8000/health
```

## HTTP status codes

| Situation                       | Status |
| ------------------------------- | ------ |
| Book created                    | 201    |
| Book updated / fetched / listed | 200    |
| Book deleted                    | 204    |
| Validation error                | 422    |
| Book not found                  | 404    |

## Tests

Tests are written in BDD (Given/When/Then) style and run against an in-memory
SQLite database, so they leave no files behind.

```bash
pytest
```

## Project layout

```
main.py          FastAPI application and routes
db.py            SQLite persistence layer
test_books.py    BDD-style integration tests
requirements.txt Python dependencies
```
