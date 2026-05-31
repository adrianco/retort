# Book Collection API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
# (optional) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The server starts on `http://localhost:5000` and creates a `books.db` SQLite
file in the working directory on first run.

## API

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check — returns `{"status":"ok"}` |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

| Field    | Type    | Required | Notes                |
|----------|---------|----------|----------------------|
| `title`  | string  | yes      | non-empty            |
| `author` | string  | yes      | non-empty            |
| `year`   | integer | no       |                      |
| `isbn`   | string  | no       |                      |

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# List all
curl http://localhost:5000/books

# Filter by author
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error / malformed JSON
- `404 Not Found` — book does not exist

## Tests

```bash
pytest
```

Tests run against a temporary SQLite database, so they don't affect `books.db`.
