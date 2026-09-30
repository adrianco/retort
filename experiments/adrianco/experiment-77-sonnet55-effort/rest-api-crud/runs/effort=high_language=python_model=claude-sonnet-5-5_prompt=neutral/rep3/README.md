# Books API

A REST API for managing a book collection. Built with the Python standard
library only (WSGI via `wsgiref`, `sqlite3`), so there is nothing to install to
run it. `pytest` is needed only for the tests.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # pytest, for the tests only
```

## Run

```bash
python -m books_api                 # http://127.0.0.1:8000, data in ./books.db
python -m books_api --port 9000 --db /tmp/my.db --host 0.0.0.0
```

## Test

```bash
python -m pytest
```

## Endpoints

| Method | Path           | Description                                   | Success |
|--------|----------------|-----------------------------------------------|---------|
| POST   | `/books`       | Create a book                                 | 201     |
| GET    | `/books`       | List books; optional `?author=` filter        | 200     |
| GET    | `/books/{id}`  | Get one book                                  | 200     |
| PUT    | `/books/{id}`  | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}`  | Delete a book                                 | 204     |
| GET    | `/health`      | Health check (`{"status": "ok"}`)             | 200     |

Book fields: `title` (required string), `author` (required string),
`year` (optional integer), `isbn` (optional string, unique).
The `author` filter is an exact, case-insensitive match. `PUT` is a full
replace: omitted optional fields are reset to `null`.

Errors are JSON `{"error": "...", "details": {...}}`:
`400` malformed JSON / non-object body, `404` unknown book or route,
`405` wrong method, `409` duplicate ISBN, `422` validation failure
(`details` maps each bad field to a message).

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Layout

- `books_api/store.py` – SQLite access (`BookStore`)
- `books_api/app.py` – WSGI app: routing, validation, JSON responses
- `books_api/__main__.py` – threaded server entry point
- `tests/test_api.py` – unit and integration tests
