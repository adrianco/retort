# Book Collection API

A REST API for managing a book collection, built with FastAPI and backed by SQLite.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Data is stored in a SQLite file
named `books.db` in the working directory (the table is created automatically
on first request). Set the `BOOKS_DB_PATH` environment variable to use a
different file path.

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## API

| Method | Path            | Description                              |
|--------|-----------------|-------------------------------------------|
| GET    | `/health`       | Health check                              |
| POST   | `/books`        | Create a book                             |
| GET    | `/books`        | List books (optional `?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book                         |
| PUT    | `/books/{id}`   | Update a book                             |
| DELETE | `/books/{id}`   | Delete a book                             |

### Book fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

`title` and `author` must be non-empty; requests missing them return `422 Unprocessable Entity`.

The `author` filter on `GET /books` performs a case-insensitive substring match.

### Example

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
```

## Tests

```bash
pytest -v
```

Tests use FastAPI's `TestClient` against a temporary SQLite file per test, so
they don't touch the `books.db` used when running the server.
