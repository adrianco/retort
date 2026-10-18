# Books API

A small REST service for managing a book collection. Written in Python using
only the standard library (`http.server` and `sqlite3`), so there are no
third-party dependencies to install.

## Requirements

- Python 3.10+
- `pytest` (only for running the tests)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest
```

## Run

```bash
python app.py            # serves on http://127.0.0.1:8000
python app.py 9000       # or pick a port
```

The database is created automatically in `books.db` in the working directory.

## Test

```bash
python -m pytest -v
```

## API

| Method | Path            | Description                              | Success |
|--------|-----------------|------------------------------------------|---------|
| POST   | `/books`        | Create a book                            | 201     |
| GET    | `/books`        | List books; optional `?author=` filter   | 200     |
| GET    | `/books/{id}`   | Get one book                             | 200     |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)  | 200     |
| DELETE | `/books/{id}`   | Delete a book                            | 204     |
| GET    | `/health`       | Health check                             | 200     |

### Book fields

| Field    | Type    | Required | Notes                              |
|----------|---------|----------|------------------------------------|
| `title`  | string  | yes      | Non-empty after trimming           |
| `author` | string  | yes      | Non-empty after trimming           |
| `year`   | integer | no       | 0–9999                             |
| `isbn`   | string  | no       | Stored as given (trimmed)          |

`author` filtering is an exact match, case-insensitive.

### Examples

```bash
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl 'localhost:8000/books?author=frank%20herbert'

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

curl -X DELETE localhost:8000/books/1
```

### Errors

Errors return JSON of the form `{"error": "...", "details": {...}}`.

- `400` — invalid JSON or failed validation (`details` maps field name to message)
- `404` — unknown route or book ID not found
- `405` — method not allowed on that route
- `500` — database error
