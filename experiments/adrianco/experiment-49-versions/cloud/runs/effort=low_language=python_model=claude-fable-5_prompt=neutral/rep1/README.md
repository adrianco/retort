# Book Collection REST API

A Flask + SQLite REST API for managing a book collection.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python app.py
```

The server listens on http://127.0.0.1:5000. The SQLite database is created
automatically at `books.db` (override with the `BOOKS_DB` env var).

## Endpoints

| Method | Path          | Description                              |
|--------|---------------|------------------------------------------|
| GET    | /health       | Health check                             |
| POST   | /books        | Create a book (title, author required)   |
| GET    | /books        | List books; supports `?author=` filter   |
| GET    | /books/{id}   | Get one book                             |
| PUT    | /books/{id}   | Update a book (partial updates allowed)  |
| DELETE | /books/{id}   | Delete a book                            |

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
```

Validation errors return `400` with an `{"errors": [...]}` body; missing
resources return `404`.

## Tests

```bash
.venv/bin/pytest -v
```
