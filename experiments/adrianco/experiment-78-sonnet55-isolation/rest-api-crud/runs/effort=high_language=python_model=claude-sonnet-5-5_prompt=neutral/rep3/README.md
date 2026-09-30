# Book Collection API

A REST API for managing books, built with Python's standard library
(`http.server`) and SQLite. No third-party runtime dependencies.

## Setup

Requires Python 3.9+.

```sh
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # only pytest, for tests
```

## Run

```sh
python src/bookapi.py
```

Environment variables: `HOST` (default `127.0.0.1`), `PORT` (default `8000`),
`BOOKS_DB` (SQLite file, default `books.db`).

## Endpoints

| Method | Path            | Description                          | Success |
|--------|-----------------|--------------------------------------|---------|
| GET    | `/health`       | Health check                         | 200     |
| POST   | `/books`        | Create a book                        | 201     |
| GET    | `/books`        | List books (`?author=` exact filter) | 200     |
| GET    | `/books/{id}`   | Get one book                         | 200     |
| PUT    | `/books/{id}`   | Replace a book                       | 200     |
| DELETE | `/books/{id}`   | Delete a book                        | 204     |

Book JSON: `{"title": str (required), "author": str (required), "year": int, "isbn": str}`.
Errors are JSON: `400` for validation/invalid JSON, `404` for unknown book/route,
`405` for unsupported methods.

```sh
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```sh
python -m pytest
```
