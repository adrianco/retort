# Book Collection REST API

A small JSON REST service for managing a book collection, written in Python using only
the standard library (`http.server` + `sqlite3`). No third-party runtime dependencies.

## Requirements

- Python 3.10+
- `pytest` (for running the tests only)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # installs pytest
```

## Run

```bash
python app.py
# Book API listening on http://127.0.0.1:8000 (db: books.db)
```

Configuration via environment variables:

| Variable   | Default     | Purpose                        |
|------------|-------------|--------------------------------|
| `HOST`     | `127.0.0.1` | Bind address                   |
| `PORT`     | `8000`      | Bind port                      |
| `BOOKS_DB` | `books.db`  | Path to the SQLite database    |
| `BOOKS_QUIET` | unset    | Set to `1` to silence access logs |

## Endpoints

| Method | Path            | Description                              | Success |
|--------|-----------------|------------------------------------------|---------|
| GET    | `/health`       | Health check                             | 200     |
| POST   | `/books`        | Create a book                            | 201     |
| GET    | `/books`        | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}`   | Fetch one book                           | 200     |
| PUT    | `/books/{id}`   | Replace a book                           | 200     |
| DELETE | `/books/{id}`   | Delete a book                            | 204     |

Book payload:

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

`title` and `author` are required non-empty strings. `year` is an optional integer
(0–9999). `isbn` is an optional ISBN-10 or ISBN-13 string (hyphens/spaces allowed).

Error responses are JSON: `400` for invalid JSON or validation failures (with a
`details` map of field errors), `404` for missing books or routes, `405` for
unsupported methods.

### Examples

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
pytest
```

The tests start the server on a random port against a temporary SQLite database and
exercise every endpoint, validation, and error paths.
