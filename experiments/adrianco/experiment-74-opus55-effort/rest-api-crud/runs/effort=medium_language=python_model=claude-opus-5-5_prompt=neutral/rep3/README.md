# Books API

A small REST API for managing a book collection. It uses only the Python standard library (`http.server` + `sqlite3`), so there's nothing to install to run it. Tests need `pytest`.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest          # only needed to run the tests
```

## Run

```bash
python books_api.py                              # http://127.0.0.1:8000, data in ./books.db
python books_api.py --host 0.0.0.0 --port 8080 --db /path/to/books.db
```

## Endpoints

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| GET | `/health` | Checks the service and database | 200 |
| POST | `/books` | Creates a book | 201 |
| GET | `/books` | Lists books; `?author=` filters by author (exact match, not case-sensitive) | 200 |
| GET | `/books/{id}` | Gets one book | 200 |
| PUT | `/books/{id}` | Replaces a book (full representation) | 200 |
| DELETE | `/books/{id}` | Deletes a book | 204 |

Book fields:

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional; 0 up to next year)
- `isbn` (string, optional; a valid ISBN-10 or ISBN-13 with 10 or 13 digits. Hyphens and spaces are removed. Each ISBN must be unique.)

Error responses are JSON, for example `{"error": "validation failed", "details": {"title": "is required"}}`:

- `400`: validation failed or the JSON is malformed
- `404`: the book or route doesn't exist
- `405`: the method isn't supported for this route
- `409`: another book already has that ISBN
- `413`: the request body is larger than 1 MiB

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Tests

```bash
python -m pytest -v
```

The tests cover:

- validation
- every route, run against an in-memory SQLite store
- data persisting in a SQLite file
- an end-to-end run over HTTP against a live server on a random port
