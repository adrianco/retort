# Books API

A small REST service for managing a book collection. Built with the Python
standard library (`http.server` and `sqlite3`), so there are no runtime
dependencies. Tests use `pytest`.

## Requirements

- Python 3.10+
- `pytest` (only for running the tests)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest
```

## Run

```bash
python books_api.py --host 127.0.0.1 --port 8000 --db books.db
```

Options:

| Flag     | Default       | Description              |
|----------|---------------|--------------------------|
| `--host` | `127.0.0.1`   | Interface to bind        |
| `--port` | `8000`        | Port to listen on        |
| `--db`   | `books.db`    | SQLite database file     |

## Test

```bash
python -m pytest -v
```

## API

A book has the shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method   | Path          | Description                                   | Success |
|----------|---------------|-----------------------------------------------|---------|
| `POST`   | `/books`      | Create a book                                 | `201`   |
| `GET`    | `/books`      | List books; optional `?author=` (case-insensitive exact match) | `200` |
| `GET`    | `/books/{id}` | Get one book                                  | `200`   |
| `PUT`    | `/books/{id}` | Update a book (any subset of fields)          | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                                 | `204`   |
| `GET`    | `/health`     | Health check                                  | `200`   |

Fields:

- `title` — required, non-empty string
- `author` — required, non-empty string
- `year` — optional integer between 0 and next calendar year
- `isbn` — optional string, ISBN-10 or ISBN-13 (digits and hyphens, `X` allowed)

On `POST`, `title` and `author` are required. On `PUT`, all fields are optional,
but any field that is sent must be valid.

### Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8000/books?author=frank%20herbert
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' -d '{"year":1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

### Errors

Errors return JSON of the form `{"error": "...", "details": {...}}`.

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| `400`  | Validation failure, malformed JSON, non-object body, missing or oversized body |
| `404`  | Unknown route or book ID does not exist                     |
| `405`  | Method not supported (for example `PATCH`)                  |
