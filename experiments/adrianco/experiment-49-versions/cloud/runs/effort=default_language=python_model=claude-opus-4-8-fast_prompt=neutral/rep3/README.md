# Book Collection API

A small REST API for managing a book collection, built with **Flask** and **SQLite**
(via Python's standard-library `sqlite3` module).

## Features

- `POST /books` — Create a new book (`title`, `author` required; `year`, `isbn` optional)
- `GET /books` — List all books, with optional `?author=` filter
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

Data is persisted in a local SQLite database (`books.db`). Responses are JSON with
appropriate HTTP status codes:

| Situation            | Status |
|----------------------|--------|
| Created              | `201`  |
| OK                   | `200`  |
| Deleted (no content) | `204`  |
| Validation error     | `400`  |
| Not found            | `404`  |

Input validation requires a non-empty `title` and `author`.

## Setup

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The API will be available at `http://127.0.0.1:8000`. (You can also run it with any WSGI
server, e.g. `flask --app app run --port 8000`.)

### Example requests

```bash
# Create a book
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}'

# List books (optionally filtered by author)
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=Andrew%20Hunt'

# Get / update / delete by ID
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Updated", "author": "Andrew Hunt", "year": 2020, "isbn": null}'
curl -X DELETE http://127.0.0.1:8000/books/1

# Health check
curl http://127.0.0.1:8000/health
```

## Tests

```bash
pytest
```

## Project layout

- `app.py` — Flask application and route handlers
- `database.py` — SQLite connection and schema initialization
- `test_app.py` — Integration tests covering the endpoints (each uses a temp DB)
- `requirements.txt` — Python dependencies
