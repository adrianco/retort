# Book Collection API

A REST API for managing a book collection, built with the Python standard
library only (WSGI + `sqlite3`). No third-party runtime dependencies.

## Setup

Requires Python 3.9+.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # only needed for running the tests (pytest)
```

## Run

```bash
python app.py
```

The server listens on `127.0.0.1:8000`. Configure with environment variables:

| Variable   | Default     | Description            |
|------------|-------------|------------------------|
| `HOST`     | `127.0.0.1` | Bind address           |
| `PORT`     | `8000`      | Bind port              |
| `BOOKS_DB` | `books.db`  | SQLite database file   |

## Endpoints

| Method | Path           | Description                                   | Success |
|--------|----------------|-----------------------------------------------|---------|
| GET    | `/health`      | Health check                                  | 200     |
| POST   | `/books`       | Create a book                                 | 201     |
| GET    | `/books`       | List books (optional `?author=` filter)       | 200     |
| GET    | `/books/{id}`  | Get one book                                  | 200     |
| PUT    | `/books/{id}`  | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}`  | Delete a book                                 | 204     |

Book fields: `title` (required string), `author` (required string),
`year` (optional integer), `isbn` (optional string). The `author` filter is an
exact, case-insensitive match.

Errors are JSON: `{"error": "...", "details": {...}}` with status 400
(validation / invalid JSON), 404 (unknown book or route), 405 (wrong method).

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
python -m pytest
```
