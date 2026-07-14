# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the server

```bash
python app.py
```

The server starts on `http://127.0.0.1:8000`. Data is persisted to `books.db`
(created automatically) in the working directory.

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List all books; filter with `?author=<name>` |
| GET    | `/books/{id}` | Get a single book                            |
| PUT    | `/books/{id}` | Update a book (partial updates supported)    |
| DELETE | `/books/{id}` | Delete a book                                |

### Status codes

- `200` — successful read/update
- `201` — book created
- `204` — book deleted
- `400` — validation error (missing/blank `title` or `author`, non-integer `year`, invalid JSON)
- `404` — book not found

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Refactoring", "author": "Martin Fowler", "year": 1999, "isbn": "978-0201485677"}'

# List, optionally filtered by author
curl 'http://127.0.0.1:8000/books?author=Martin%20Fowler'

# Get one
curl http://127.0.0.1:8000/books/1

# Update (partial)
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 2018}'

# Delete
curl -X DELETE http://127.0.0.1:8000/books/1
```

## Run the tests

```bash
pytest
```

Tests use a temporary SQLite database per test, so they never touch `books.db`.
