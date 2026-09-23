# Book Collection API

A small REST API for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so the service itself has no
third-party dependencies.

## Requirements

- Python 3.9+
- `pytest` (only for running the tests)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
# Book API listening on http://127.0.0.1:8000 (db: books.db)
```

Environment variables:

| Variable        | Default     | Purpose                                  |
|-----------------|-------------|------------------------------------------|
| `HOST`          | `127.0.0.1` | Bind address                             |
| `PORT`          | `8000`      | Port                                     |
| `BOOKS_DB`      | `books.db`  | SQLite file path (`:memory:` for ephemeral) |
| `BOOKS_API_LOG` | unset       | Set to any value to enable request logs  |

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check → `{"status": "ok"}`    | 200 |
| POST   | `/books`      | Create a book                        | 201 (+ `Location` header) |
| GET    | `/books`      | List books; `?author=` filter (exact match, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get a single book                    | 200 |
| PUT    | `/books/{id}` | Replace a book (full update)         | 200 |
| DELETE | `/books/{id}` | Delete a book                        | 204 |

### Book fields

| Field    | Type    | Rules |
|----------|---------|-------|
| `title`  | string  | **required**, non-empty |
| `author` | string  | **required**, non-empty |
| `year`   | integer | optional, -9999..9999 |
| `isbn`   | string  | optional, valid ISBN-10 or ISBN-13 shape (hyphens/spaces allowed) |

Unknown fields are rejected. `PUT` replaces the whole record, so optional
fields left out become `null`.

### Errors

Errors are JSON: `{"error": "...", "details": {...}}`.

- `400` — malformed JSON body or non-integer id
- `404` — book or route not found
- `405` — method not allowed on `/books` (PUT/DELETE) or `/books/{id}` (POST)
- `422` — validation failed; `details` maps field → message

## Example

```bash
curl -s -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
curl -s 'localhost:8000/books?author=Frank%20Herbert'
curl -s -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -s -X DELETE -i localhost:8000/books/1
```

## Tests

```bash
pytest -q
```

The tests in `test_app.py` start a real server on an ephemeral port with a
temporary SQLite file and exercise every endpoint, validation rules, error
codes, the author filter, and persistence across restarts.
