# Book Collection API

A REST API for managing a book collection, written with the Python standard
library only (`http.server` + `sqlite3`) — no runtime dependencies.

## Setup

Requires Python 3.9+. Tests need `pytest`:

```bash
python -m venv venv
venv/bin/pip install pytest
```

## Run

```bash
venv/bin/python app.py
```

Configuration via environment variables: `HOST` (default `127.0.0.1`),
`PORT` (default `8000`), `BOOKS_DB` (SQLite file, default `books.db`).

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book fields: `title` (required string), `author` (required string),
`year` (optional integer), `isbn` (optional string). PUT is a full
replacement, so `title` and `author` are required there too.

Errors are returned as `{"error": "..."}` with 400 (validation / bad JSON),
404 (not found) or 405 (method not allowed). The `author` filter is an
exact, case-insensitive match.

```bash
curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Test

```bash
venv/bin/python -m pytest
```
