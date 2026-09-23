# Book Collection API

A small REST API for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so it has no runtime dependencies.
You need `pytest` only to run the tests.

## Requirements

- Python 3.9+
- `pytest` (for tests only)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest
```

## Run

```bash
python app.py
# Book API listening on http://127.0.0.1:8000 (db: books.db)
```

Environment variables:

| Variable      | Default     | Description                  |
|---------------|-------------|------------------------------|
| `HOST`        | `127.0.0.1` | Bind address                 |
| `PORT`        | `8000`      | Listen port                  |
| `BOOKS_DB`    | `books.db`  | SQLite database file path    |
| `BOOKS_QUIET` | unset       | Set to disable request logs  |

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check (also checks the database)      | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filter (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book                               | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Book fields:

- `title` (string, required, non-empty)
- `author` (string, required, non-empty)
- `year` (integer, optional)
- `isbn` (string, optional, valid ISBN-10 or ISBN-13 format; hyphens/spaces allowed)

Errors are returned as JSON:

- `400`: validation failure or malformed JSON:
  `{"error": "Validation failed", "details": {"title": "..."}}`
- `404`: book or route not found
- `405`: method not allowed

### Examples

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Tests

```bash
python -m pytest
```

The integration tests start a real server on a random port with a temporary
SQLite database and call it over HTTP. There are also unit tests for
validation and persistence.
