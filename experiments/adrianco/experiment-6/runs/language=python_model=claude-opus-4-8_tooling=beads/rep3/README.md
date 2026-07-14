# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite**.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the server

```bash
# Option A: run the module directly (listens on port 5000 by default)
python app.py

# Option B: use the Flask CLI
flask --app app run --port 5000
```

The SQLite database file (`books.db`) is created automatically on first run.
Override its location with the `BOOKS_DB` environment variable and the port
with `PORT`:

```bash
BOOKS_DB=/tmp/books.db PORT=8080 python app.py
```

## API

| Method | Path           | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Health check — returns `{"status": "ok"}`     |
| POST   | `/books`       | Create a book                                 |
| GET    | `/books`       | List books (optional `?author=` filter)       |
| GET    | `/books/{id}`  | Get a single book                             |
| PUT    | `/books/{id}`  | Update a book (partial updates supported)     |
| DELETE | `/books/{id}`  | Delete a book                                 |

### Book fields

| Field    | Type    | Required | Notes                          |
| -------- | ------- | -------- | ------------------------------ |
| `title`  | string  | yes      | Non-empty                      |
| `author` | string  | yes      | Non-empty                      |
| `year`   | integer | no       |                                |
| `isbn`   | string  | no       |                                |

### Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation error (e.g. missing `title`/`author`)
- `404 Not Found` — book ID does not exist

### Examples

```bash
# Create
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'

# List, filtered by author
curl 'localhost:5000/books?author=Frank%20Herbert'

# Get one
curl localhost:5000/books/1

# Update (partial)
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' -d '{"year": 1990}'

# Delete
curl -X DELETE localhost:5000/books/1
```

## Tests

```bash
python -m pytest
```

Tests run against a fresh temporary database per test, so they are isolated
and order-independent.
