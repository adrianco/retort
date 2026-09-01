# Book Collection API

A small REST service for managing a collection of books, built with
**Python 3 / Flask** and backed by an embedded **SQLite** database.

## Endpoints

| Method | Path                     | Description                                   | Success |
|--------|--------------------------|-----------------------------------------------|---------|
| GET    | `/health`                | Liveness + database check                     | 200     |
| POST   | `/books`                 | Create a book                                 | 201     |
| GET    | `/books`                 | List books; optional `?author=` filter        | 200     |
| GET    | `/books/{id}`            | Fetch a single book                           | 200     |
| PUT    | `/books/{id}`            | Replace a book (title and author required)    | 200     |
| PATCH  | `/books/{id}`            | Partially update a book                       | 200     |
| DELETE | `/books/{id}`            | Delete a book                                 | 204     |

Book fields: `title` (required), `author` (required), `year` (optional integer
0–9999), `isbn` (optional, ISBN-10 or ISBN-13, hyphens/spaces allowed).

Error responses are JSON:

```json
{ "error": "validation failed", "details": { "title": "is required" } }
```

Status codes used: `400` invalid body / validation failure, `404` unknown book
or route, `405` wrong method, `415` non-JSON content type on write endpoints.

The `?author=` filter is an exact, case-insensitive match.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # or requirements.txt for runtime only
```

## Run

```bash
python app.py
# or
flask --app app run --port 8000
```

The server listens on `http://127.0.0.1:8000` by default. Override with the
`HOST` and `PORT` environment variables. The SQLite file defaults to
`books.db` next to `app.py`; set `BOOKS_DB=/path/to/file.db` to change it.
Tables are created automatically on startup.

### Example requests

```bash
curl -s localhost:8000/health

curl -s -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -s 'localhost:8000/books?author=Frank%20Herbert'
curl -s localhost:8000/books/1
curl -s -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -s -X DELETE localhost:8000/books/1 -i
```

## Test

```bash
pytest            # runs tests/ (14 tests)
pytest --cov=.    # with coverage
```

Tests use a throwaway SQLite file per test via the `create_app` factory, so
they never touch `books.db`.

## Layout

```
app.py              Flask app factory, validation, routes
db.py               SQLite connection handling and schema
tests/              pytest suite (conftest.py + test_books.py)
requirements*.txt   dependencies
```
