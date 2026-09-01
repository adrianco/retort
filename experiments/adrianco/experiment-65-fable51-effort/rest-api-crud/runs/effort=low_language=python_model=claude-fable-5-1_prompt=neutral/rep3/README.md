# Book Collection REST API

A small JSON REST service for managing a book collection, built on the Python
standard library (`http.server` + `sqlite3`). No third-party runtime dependencies.

## Requirements

- Python 3.10+
- `pytest` for running the tests

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install pytest
```

## Run

```bash
python -m src.app --host 127.0.0.1 --port 8000 --db books.db
```

The SQLite database file is created automatically.

## Endpoints

| Method | Path                  | Description                                  |
|--------|-----------------------|----------------------------------------------|
| GET    | `/health`             | Health check, returns `{"status": "ok"}`     |
| POST   | `/books`              | Create a book (201)                          |
| GET    | `/books`              | List books, optional `?author=` exact filter |
| GET    | `/books/{id}`         | Get one book (404 if missing)                |
| PUT    | `/books/{id}`         | Replace a book (200 / 404)                   |
| DELETE | `/books/{id}`         | Delete a book (204 / 404)                    |

Book payload: `{"title": str, "author": str, "year": int?, "isbn": str?}`.
`title` and `author` are required and non-empty; `year` must be an integer
0–9999; `isbn` must be 10 or 13 alphanumeric characters (hyphens/spaces ignored).
Validation failures return `422` with a `details` map; malformed JSON returns `400`.

Example:

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
python -m pytest -q
```
