# Book Collection API

A REST API for managing books, built with the Python standard library only
(WSGI + `sqlite3`). No third-party runtime dependencies. Requires Python 3.9+.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # pytest, for tests only
```

## Run

```bash
python app.py
```

Environment variables: `PORT` (default `8000`), `HOST` (default `127.0.0.1`),
`BOOKS_DB` (SQLite file path, default `books.db`).

## Test

```bash
python -m pytest -v
```

## Endpoints

| Method | Path            | Description                               | Success |
|--------|-----------------|-------------------------------------------|---------|
| POST   | `/books`        | Create a book                             | 201     |
| GET    | `/books`        | List books (optional `?author=` filter, case-insensitive exact match) | 200 |
| GET    | `/books/{id}`   | Get one book                              | 200     |
| PUT    | `/books/{id}`   | Replace a book's fields                   | 200     |
| DELETE | `/books/{id}`   | Delete a book                             | 200     |
| GET    | `/health`       | Health check → `{"status": "ok"}`         | 200     |

Book fields: `title` (required string), `author` (required string),
`year` (optional integer), `isbn` (optional string).

Errors return JSON `{"error": "..."}`: `400` malformed JSON/body, `404` unknown
book or route, `405` wrong method, `422` validation failure (with `details`).

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```
