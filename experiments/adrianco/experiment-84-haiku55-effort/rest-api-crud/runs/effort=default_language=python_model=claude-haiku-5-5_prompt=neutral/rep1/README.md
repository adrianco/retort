# Books API

A REST API for managing a book collection, stored in SQLite. It uses only the
Python standard library for the server (`http.server` + `sqlite3`), so there is
nothing to install to run it. `pytest` is only needed to run the tests.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest      # only needed for the tests
```

## Run

```bash
python books_api.py                          # http://127.0.0.1:8000, database ./books.db
python books_api.py --port 9000 --db my.db   # custom port and database file
```

The database path can also be set with the `BOOKS_DB` environment variable.
The `--db` flag takes precedence over it.

## Test

```bash
python -m pytest -v
```

## API

All requests and responses use JSON. Errors are returned as `{"error": "<message>"}`.

| Method   | Path          | Description                                  | Success       |
|----------|---------------|----------------------------------------------|---------------|
| `POST`   | `/books`      | Create a book                                | `201` + book  |
| `GET`    | `/books`      | List books; optional `?author=` filter       | `200` + array |
| `GET`    | `/books/{id}` | Get one book                                 | `200` + book  |
| `PUT`    | `/books/{id}` | Update a book (any subset of fields)         | `200` + book  |
| `DELETE` | `/books/{id}` | Delete a book                                | `204`         |
| `GET`    | `/health`     | Health check                                 | `200`         |

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

### Fields and validation

| Field    | Required | Rules                                                       |
|----------|----------|-------------------------------------------------------------|
| `title`  | yes      | non-empty string                                            |
| `author` | yes      | non-empty string                                            |
| `year`   | no       | integer from 1 to next calendar year; `null` allowed        |
| `isbn`   | no       | 10 or 13 digits (last character of an ISBN-10 may be `X`); hyphens and spaces are stripped; `null` allowed |

- On `POST`, `title` and `author` must be present.
- On `PUT`, fields are optional. Any field that is supplied must be valid, and omitted fields keep their current values.
- The `?author=` filter matches the full author name, ignoring case.

### Examples

```bash
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'

curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' -d '{"year": 1966}'

curl -i -X DELETE http://127.0.0.1:8000/books/1
```

### Status codes

| Code  | When                                                                 |
|-------|----------------------------------------------------------------------|
| `200` | Successful read or update                                            |
| `201` | Book created (response includes a `Location` header)                 |
| `204` | Book deleted                                                         |
| `400` | Invalid JSON, a non-object body, or a failed validation rule         |
| `404` | Unknown path, or no book with that ID                                |
| `405` | Method not supported on that path (response includes an `Allow` header) |

## Files

- `books_api.py`: server, routing, validation, and SQLite storage
- `test_books_api.py`: integration tests that run a live server on an ephemeral port
