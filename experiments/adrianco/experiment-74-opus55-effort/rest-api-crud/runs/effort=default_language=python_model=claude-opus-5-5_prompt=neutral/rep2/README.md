# Book Collection API

A small REST API for managing a book collection, written in Python using only
the standard library (`http.server` + `sqlite3`). No runtime dependencies.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python app.py
```

Environment variables:

| Variable   | Default     | Purpose                |
|------------|-------------|------------------------|
| `HOST`     | `127.0.0.1` | Bind address           |
| `PORT`     | `8000`      | Listen port            |
| `BOOKS_DB` | `books.db`  | SQLite database file   |

## Endpoints

| Method | Path           | Description                                  | Success |
|--------|----------------|----------------------------------------------|---------|
| GET    | `/health`      | Health check (also pings the database)       | 200     |
| POST   | `/books`       | Create a book                                | 201     |
| GET    | `/books`       | List books; `?author=` filter (case-insensitive exact match) | 200 |
| GET    | `/books/{id}`  | Get one book                                 | 200     |
| PUT    | `/books/{id}`  | Replace a book                               | 200     |
| DELETE | `/books/{id}`  | Delete a book                                | 204     |

Book JSON: `{"title": str, "author": str, "year": int|null, "isbn": str|null}`.

Validation rules:
- `title` and `author` are required, non-empty strings.
- `year` is optional and must be an integer.
- `isbn` is optional and must be a valid ISBN-10 or ISBN-13 (hyphens/spaces allowed).
- Unknown fields are rejected.

Error responses are JSON: `{"error": "...", "details": {...}}`.
Status codes: `400` malformed JSON, `422` validation failure, `404` not found,
`405` wrong method on a known path.

### Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
python -m pytest -q
```

The tests cover validation unit tests plus HTTP integration tests that start a
real server on an ephemeral port against a temporary SQLite database.
