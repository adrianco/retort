# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (Python standard-library `sqlite3` — no database server needed).

## Requirements

- Python 3.9+
- Flask and pytest (see `requirements.txt`)

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(If Flask and pytest are already installed system-wide, you can skip the venv.)

## Run the server

```sh
python3 app.py
# or: flask --app app run --port 8000
```

The API listens on `http://127.0.0.1:8000`. Data is stored in `books.db`
next to `app.py`; the file and schema are created automatically on first
start. Set the `BOOKS_DB` environment variable to use a different path.

## Run the tests

```sh
python3 -m pytest -v
```

Tests run against a temporary database, so they never touch `books.db`.

## API

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check (also pings the database)   | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

### Book fields

| Field    | Type    | Notes                                   |
|----------|---------|-----------------------------------------|
| `title`  | string  | **required**, must be non-empty         |
| `author` | string  | **required**, must be non-empty         |
| `year`   | integer | optional                                |
| `isbn`   | string  | optional                                |

Validation errors return **400** with per-field details; unknown fields are
rejected. `PUT` is a full replace: `title` and `author` are required and
omitted optional fields are reset to `null`. The `?author=` filter is a
case-insensitive exact match. Missing books return **404**, and all errors
(including unknown routes and wrong methods) are JSON:

```json
{"error": "validation failed", "details": {"title": "is required"}}
```

### Examples

```sh
# Create
curl -s -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974, "isbn": "978-0061054884"}'
# -> 201 {"id": 1, "title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974, "isbn": "978-0061054884"}

# List / filter
curl -s http://127.0.0.1:8000/books
curl -s 'http://127.0.0.1:8000/books?author=Ursula%20K.%20Le%20Guin'

# Get one
curl -s http://127.0.0.1:8000/books/1

# Replace
curl -s -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "year": 1969}'

# Delete
curl -s -X DELETE http://127.0.0.1:8000/books/1 -i
```

## Project layout

| File          | Purpose                                            |
|---------------|----------------------------------------------------|
| `app.py`      | Flask app factory, routes, validation, JSON errors |
| `db.py`       | SQLite schema and per-request connection helpers   |
| `test_app.py` | Integration tests (pytest + Flask test client)     |
