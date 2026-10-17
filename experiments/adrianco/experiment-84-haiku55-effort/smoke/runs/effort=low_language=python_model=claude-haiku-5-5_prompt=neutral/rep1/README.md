# Books API

A REST API for managing a book collection. Built with Python's standard
library (`http.server`) and SQLite (`sqlite3`), so the service itself has no
third-party dependencies. `pytest` is only needed to run the tests.

## Requirements

- Python 3.8 or newer

## Setup

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt   # installs pytest for the test suite
```

## Run

```sh
python books_api.py --port 8000 --db books.db
```

Options:

| Flag     | Default       | Description                          |
|----------|---------------|--------------------------------------|
| `--host` | `127.0.0.1`   | Interface to bind to                 |
| `--port` | `8000`        | Port to listen on (`0` picks a free port) |
| `--db`   | `books.db`    | SQLite database file (created if missing) |

## Test

```sh
python -m pytest -q
```

## API

All responses are JSON. Errors have the shape `{"error": "<message>"}`.

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method   | Path          | Description                          | Success |
|----------|---------------|--------------------------------------|---------|
| `POST`   | `/books`      | Create a book                        | `201`   |
| `GET`    | `/books`      | List books; optional `?author=` filter (case-insensitive exact match) | `200` |
| `GET`    | `/books/{id}` | Get one book                         | `200`   |
| `PUT`    | `/books/{id}` | Update a book (send any subset of fields) | `200` |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`   |
| `GET`    | `/health`     | Health check (verifies DB is reachable) | `200` |

### Fields

| Field    | Type    | Required | Rules                                   |
|----------|---------|----------|-----------------------------------------|
| `title`  | string  | yes      | non-empty after trimming                |
| `author` | string  | yes      | non-empty after trimming                |
| `year`   | integer | no       | `0`–`9999`; `null` clears it            |
| `isbn`   | string  | no       | 10–20 characters of digits, `X`, hyphens or spaces; `null` clears it |

Unknown fields are rejected with `400`.

### Status codes

| Code  | When                                                       |
|-------|------------------------------------------------------------|
| `200` | Success                                                    |
| `201` | Book created                                               |
| `204` | Book deleted (no body)                                     |
| `400` | Invalid JSON, missing/invalid field, unknown field, empty body |
| `404` | Unknown route or book ID not found                         |
| `405` | Method not supported on that route (response includes `Allow`) |
| `413` | Request body larger than 1 MB                              |
| `503` | Health check failed to reach the database                  |

## Examples

```sh
# Create
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# List / filter
curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'

# Get
curl localhost:8000/books/1

# Update
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -i -X DELETE localhost:8000/books/1

# Health
curl localhost:8000/health
```

## Project layout

```
books_api.py        # server, routing, validation, SQLite storage
test_books_api.py   # unit and integration tests
requirements.txt    # test dependencies
```
