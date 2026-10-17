# Book Collection API

A REST API for managing a book collection, backed by SQLite. It uses only the
Python standard library at runtime (`http.server` and `sqlite3`), so there are
no packages to install to run it. pytest is needed only to run the tests.

## Requirements

- Python 3 (tested on 3.13)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # pytest, for running the tests
```

## Run

```bash
python app.py                              # http://127.0.0.1:8000, database ./books.db
python app.py --port 9000 --db /tmp/b.db   # custom port and database file
python app.py --host 0.0.0.0               # listen on all interfaces
```

Options: `--host` (default `127.0.0.1`), `--port` (default `8000`), `--db`
(default `books.db`, created on first run).

## Test

```bash
python -m pytest -v
```

The suite has 40 tests. `test_validation.py` covers the validation rules, and
`test_api.py` starts a real HTTP server on a free port and exercises every
endpoint, including persistence across restarts.

## Data model

| Field    | Type    | Required | Notes                                                       |
|----------|---------|----------|-------------------------------------------------------------|
| `id`     | integer | (server) | Assigned on create                                          |
| `title`  | string  | yes      | Non-blank, at most 500 characters                           |
| `author` | string  | yes      | Non-blank, at most 500 characters                           |
| `year`   | integer | no       | Between 1000 and next calendar year                         |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13, hyphens and spaces allowed (see below)  |

Text fields are trimmed of surrounding whitespace. `isbn` is stored with hyphens
and spaces removed and upper-cased, so `978-0-441-01359-3` is returned as
`9780441013593`. The format is checked but the check digit is not. Unknown
fields are ignored.

## Endpoints

| Method   | Path          | Success               | Description                                   |
|----------|---------------|-----------------------|-----------------------------------------------|
| `POST`   | `/books`      | `201 Created`         | Create a book. `Location` header gives its URL |
| `GET`    | `/books`      | `200 OK`              | List all books. Supports `?author=` filter    |
| `GET`    | `/books/{id}` | `200 OK`              | Get one book                                  |
| `PUT`    | `/books/{id}` | `200 OK`              | Replace a book. `title` and `author` required |
| `DELETE` | `/books/{id}` | `204 No Content`      | Delete a book                                 |
| `GET`    | `/health`     | `200 OK`              | Health check. Returns `503` if the DB is down |

`?author=` matches the author name exactly, ignoring case (`?author=jane austen`
matches `Jane Austen`). A blank value returns `400`.

`PUT` replaces the whole record, so `title` and `author` must be sent again.
Omitting `year` or `isbn` clears them.

### Status codes

- `400` for invalid JSON, a non-object body, or failed validation
- `404` for an unknown book or unknown path. A non-numeric id such as `/books/abc` also returns `404`
- `405` for an unsupported method on a known path. The `Allow` header lists the valid methods
- `500` for unexpected server errors

Errors are JSON. Validation failures list every bad field at once:

```json
{"error": "validation failed", "details": {"title": "is required", "author": "is required"}}
```

## Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get, update, delete
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Project layout

| File                | Purpose                                              |
|---------------------|------------------------------------------------------|
| `app.py`            | HTTP server, routing, JSON responses, CLI entry point |
| `db.py`             | SQLite storage (schema and queries)                  |
| `validation.py`     | Input validation and ISBN normalisation              |
| `test_validation.py`| Unit tests for validation                            |
| `test_api.py`       | Integration tests over real HTTP                     |
| `requirements-dev.txt` | Test dependencies                                 |
