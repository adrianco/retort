# Book Collection REST API

A small Flask service for managing a book collection, backed by SQLite.

## Requirements

- Python 3.9+
- Flask, pytest (see `requirements.txt`)

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
python3 app.py
```

The server listens on `http://127.0.0.1:5000`. Data is stored in `books.db`
in the working directory (override with the `BOOKS_DB` environment variable).

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — `{"status": "ok"}`            |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List books; filter with `?author=<name>`     |
| GET    | `/books/{id}` | Get one book                                 |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book (returns 204)                  |

Validation errors return `400` with `{"errors": [...]}`; missing books return
`404` with `{"error": "book not found"}`.

### Examples

```sh
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' -d '{"year": 1966}'

curl -X DELETE http://127.0.0.1:5000/books/1
```

## Tests

```sh
pytest
```

Tests live in `test_app.py` and cover health, CRUD, validation, and the
author filter using a temporary database per test.
