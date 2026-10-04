# Book Collection API

A small REST API for managing books, written in Python using only the standard
library (`http.server` + `sqlite3`). There are no runtime dependencies.

## Setup

Requires Python 3.9+. Only the tests need a third-party package:

```bash
python3 -m venv venv
venv/bin/pip install pytest
```

## Run

```bash
venv/bin/python app.py                 # http://127.0.0.1:8000, data in ./books.db
venv/bin/python app.py --port 9000 --db /tmp/books.db
```

Options may also be set with the `HOST`, `PORT` and `BOOKS_DB` environment variables.

## Test

```bash
venv/bin/python -m pytest
```

The tests start the real server on an ephemeral port with a temporary SQLite file.

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book (full update)         | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

A book is `{"id", "title", "author", "year", "isbn"}`. `title` and `author` are
required non-empty strings; `year` (integer) and `isbn` (string) are optional and
default to `null`. `PUT` replaces the whole record, so omitted optional fields are
reset to `null`.

Errors are JSON: `{"error": "..."}`, with a per-field `details` object for
validation failures.

| Status | Meaning                                   |
|--------|-------------------------------------------|
| 400    | Malformed JSON or validation failure      |
| 404    | Unknown route or book ID                  |
| 405    | Method not supported on that route        |
| 413    | Request body larger than 1 MB             |

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
```
