# Book Collection REST API

A small REST service for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so it has no runtime dependencies.

## Requirements

- Python 3.10+
- `pytest`, only for running the tests

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python app.py                      # http://127.0.0.1:8000, data in ./books.db
python app.py --host 0.0.0.0 --port 9000 --db /path/to/books.db
```

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check: `{"status": "ok"}`             | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filter (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book (full representation)         | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Book body:

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

Validation rules:
- `title` and `author` are required non-empty strings.
- `year` is optional and must be an integer.
- `isbn` is optional and must be a valid ISBN-10 or ISBN-13. Hyphens and spaces are allowed.

Errors return JSON, for example
`{"error": "validation failed", "details": {"title": "..."}}` with status `400`,
or `{"error": "book not found"}` with status `404`.

### Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title":"Emma","author":"Jane Austen","year":1815}'
curl 'localhost:8000/books?author=Jane%20Austen'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
     -d '{"title":"Emma","author":"Jane Austen","year":1816}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
pytest -q tests
```

The tests start a real server on a free port against a temporary SQLite file.
They cover CRUD, the author filter, validation, 404s and persistence across restarts.
