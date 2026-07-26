# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:5000`. Data is stored in `books.db`
(override with the `BOOKS_DB_PATH` environment variable).

## Endpoints

| Method | Path          | Description                                |
|--------|---------------|--------------------------------------------|
| GET    | `/health`     | Health check                               |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List all books; filter with `?author=Name` |
| GET    | `/books/{id}` | Get one book                               |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)    |
| DELETE | `/books/{id}` | Delete a book                              |

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List / filter
curl http://127.0.0.1:5000/books
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

# Get / update / delete
curl http://127.0.0.1:5000/books/1
curl -X PUT http://127.0.0.1:5000/books/1 -H 'Content-Type: application/json' -d '{"year": 1966}'
curl -X DELETE http://127.0.0.1:5000/books/1
```

### Status codes

- `200` success, `201` created, `204` deleted
- `400` validation error (missing/empty `title` or `author`, wrong types, invalid JSON)
- `404` book not found

## Tests

```bash
pytest -v
```
