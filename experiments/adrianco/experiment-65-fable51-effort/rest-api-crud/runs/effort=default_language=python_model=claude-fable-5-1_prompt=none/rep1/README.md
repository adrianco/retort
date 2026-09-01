# Books API

A small REST service for managing a book collection, built with **Flask** and
**SQLite** (Python standard library `sqlite3`, no ORM).

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py
# -> http://127.0.0.1:8000
```

Environment variables:

| Variable         | Default      | Purpose                         |
|------------------|--------------|---------------------------------|
| `BOOKS_DATABASE` | `books.db`   | Path to the SQLite database file |
| `HOST`           | `127.0.0.1`  | Bind address                     |
| `PORT`           | `8000`       | Bind port                        |
| `FLASK_DEBUG`    | unset        | Set to `1` for auto-reload       |

The database file and schema are created automatically on first start.

## Test

```bash
pytest
```

## API

All responses are JSON. Errors have the shape
`{"error": "...", "details": ["..."]}` (`details` only on validation errors).

| Method | Path                   | Success | Notes                                   |
|--------|------------------------|---------|-----------------------------------------|
| GET    | `/health`              | 200     | `{"status":"ok","database":"ok"}`       |
| POST   | `/books`               | 201     | Body: `title`*, `author`*, `year`, `isbn`. Sets `Location` header. |
| GET    | `/books`               | 200     | Optional `?author=` (case-insensitive exact match) |
| GET    | `/books/{id}`          | 200     | 404 if missing                          |
| PUT    | `/books/{id}`          | 200     | Partial update; any subset of fields    |
| DELETE | `/books/{id}`          | 204     | 404 if missing                          |

\* required

### Validation rules

- `title`, `author`: non-empty strings (required on create).
- `year`: integer 0–9999, or `null`.
- `isbn`: 10- or 13-character ISBN (hyphens/spaces allowed, stripped on save), or `null`.
- Unknown fields are rejected with 400.

### Examples

```bash
curl -s -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s 'localhost:8000/books?author=Frank%20Herbert'
curl -s localhost:8000/books/1
curl -s -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' -d '{"year":1966}'
curl -s -X DELETE localhost:8000/books/1 -i
```

## Layout

```
app/__init__.py   application factory, JSON error handlers
app/db.py         SQLite connection lifecycle + schema
app/routes.py     /health and /books endpoints, validation
run.py            dev server entry point
tests/            pytest suite (Flask test client, temp DB per test)
```
