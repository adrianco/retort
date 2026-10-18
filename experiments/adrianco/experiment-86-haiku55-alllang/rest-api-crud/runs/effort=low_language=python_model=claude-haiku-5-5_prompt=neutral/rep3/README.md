# Book Collection API

A small REST service for managing a book collection. It is built on the Python
standard library (`http.server` + `sqlite3`), so there are no runtime
dependencies. `pytest` is only needed to run the tests.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest
```

## Run

```bash
python -m bookapi --port 8000 --db books.db
```

Options:

| Flag     | Default       | Description                                      |
|----------|---------------|--------------------------------------------------|
| `--host` | `127.0.0.1`   | Interface to bind to                             |
| `--port` | `8000`        | Port to listen on                                |
| `--db`   | `books.db`    | SQLite file path (or set `BOOKS_DB_PATH`)        |

## Test

```bash
python -m pytest
```

## Data model

| Field    | Type    | Required | Notes                                          |
|----------|---------|----------|------------------------------------------------|
| `id`     | integer | –        | Assigned by the server                         |
| `title`  | string  | yes      | Non-empty; surrounding whitespace is trimmed   |
| `author` | string  | yes      | Non-empty; surrounding whitespace is trimmed   |
| `year`   | integer | no       | Between 1 and next calendar year               |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13; hyphens/spaces removed; unique |

## Endpoints

| Method | Path          | Success | Description                                  |
|--------|---------------|---------|----------------------------------------------|
| POST   | `/books`      | 201     | Create a book                                |
| GET    | `/books`      | 200     | List books; optional `?author=` (case-insensitive exact match) |
| GET    | `/books/{id}` | 200     | Get one book                                 |
| PUT    | `/books/{id}` | 200     | Replace a book's fields (full update)        |
| DELETE | `/books/{id}` | 200     | Delete a book; returns `{"deleted": true, "id": ...}` |
| GET    | `/health`     | 200     | Health check: `{"status": "ok"}`             |

### Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Errors

All errors are JSON of the form `{"error": "<message>"}`. Validation failures
also include `"details"`, a map of field name to message.

| Status | When                                              |
|--------|---------------------------------------------------|
| 400    | Invalid JSON, missing/invalid fields              |
| 404    | Unknown path or book ID not found                 |
| 405    | Method not supported on that path                 |
| 409    | `isbn` already used by another book               |
