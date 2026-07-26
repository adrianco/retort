# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (Python's built-in `sqlite3` module — no separate database server
needed).

## Requirements

- Python 3.10+
- Flask (and pytest for the tests)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` by default (port 8000 rather
than Flask's usual 5000, which macOS AirPlay often occupies). Configuration is
via environment variables:

| Variable   | Default    | Purpose                          |
|------------|------------|----------------------------------|
| `HOST`     | `127.0.0.1`| Bind address                     |
| `PORT`     | `8000`     | Listen port                      |
| `BOOKS_DB` | `books.db` | Path to the SQLite database file |

The database file and schema are created automatically on startup.

## Run the tests

```bash
python -m pytest -v
```

The tests spin the app up against a temporary database per test, so they never
touch `books.db`.

## API

All responses are JSON. Errors have the shape
`{"error": "...", "details": {field: message, ...}}` (`details` appears on
validation failures).

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books, optional `?author=` filter | 200  |
| GET    | `/books/{id}` | Fetch one book                       | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

### Book fields

| Field    | Type    | Rules                                  |
|----------|---------|----------------------------------------|
| `title`  | string  | **Required**, must be non-blank        |
| `author` | string  | **Required**, must be non-blank        |
| `year`   | integer | Optional                               |
| `isbn`   | string  | Optional                               |

Invalid payloads get `400` with per-field messages; unknown fields are
ignored. Missing books get `404`. `PUT` is a full replacement: omitting
`year`/`isbn` resets them to `null`. The `?author=` filter is a
case-insensitive exact match.

### Examples

```bash
# Health check
curl http://127.0.0.1:8000/health

# Create
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'

# List all / filter by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=J.R.R.%20Tolkien'

# Get one
curl http://127.0.0.1:8000/books/1

# Update (full replacement)
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1951}'

# Delete
curl -X DELETE http://127.0.0.1:8000/books/1
```

## Project layout

| File               | Purpose                                      |
|--------------------|----------------------------------------------|
| `app.py`           | Flask app factory, routes, validation, SQLite helpers |
| `test_app.py`      | pytest integration tests                     |
| `requirements.txt` | Dependencies                                 |
