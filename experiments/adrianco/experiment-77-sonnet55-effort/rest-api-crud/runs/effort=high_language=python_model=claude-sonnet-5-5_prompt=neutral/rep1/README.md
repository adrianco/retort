# Book Collection API

A REST API for managing a book collection, written in Python using only the
standard library (WSGI + `sqlite3`) — no third-party runtime dependencies.

## Setup

Requires Python 3.9+.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # only pytest, for the tests
```

## Run

```bash
python app.py
```

The server listens on `127.0.0.1:8000`. Configure with environment variables:

| Variable   | Default     | Purpose                |
|------------|-------------|------------------------|
| `HOST`     | `127.0.0.1` | Bind address           |
| `PORT`     | `8000`      | Bind port              |
| `BOOKS_DB` | `books.db`  | SQLite database path   |

`app.create_app(db_path)` returns a WSGI app if you want to serve it with
another WSGI server (e.g. `gunicorn "app:create_app()"`).

## Endpoints

| Method | Path           | Description                                | Success |
|--------|----------------|--------------------------------------------|---------|
| GET    | `/health`      | Health check                               | 200     |
| POST   | `/books`       | Create a book                              | 201     |
| GET    | `/books`       | List books (`?author=` filter, case-insensitive exact match) | 200 |
| GET    | `/books/{id}`  | Get one book                               | 200     |
| PUT    | `/books/{id}`  | Replace a book                             | 200     |
| DELETE | `/books/{id}`  | Delete a book                              | 204     |

Book JSON: `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}`

- `title` and `author` are required, non-empty strings.
- `year` (integer) and `isbn` (string) are optional.
- `PUT` replaces the whole record, so `title` and `author` are required and omitted optional fields are cleared.

Errors are JSON: `{"error": "Validation failed", "details": {"title": "..."}}` with
status 400 (invalid input), 404 (unknown book/route), 405 (wrong method) or 413 (body too large).

## Example

```bash
curl -i -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
python -m pytest
```
