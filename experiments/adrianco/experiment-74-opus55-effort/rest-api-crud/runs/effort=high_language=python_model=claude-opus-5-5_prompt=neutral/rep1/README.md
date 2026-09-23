# Books API

A small REST API for managing a book collection, written in Python using
**only the standard library**: `wsgiref` serves HTTP and `sqlite3` stores the data.
Nothing needs installing to run it; pytest is only needed for the tests.

## Requirements

- Python 3.10+ (developed on 3.14)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python -m books_api                    # http://127.0.0.1:8000, data in ./books.db
python -m books_api --port 9000 --db /tmp/books.db
python -m books_api --db :memory:      # throwaway in-memory database
```

You can also set these with the `BOOKS_HOST`, `BOOKS_PORT` and `BOOKS_DB` environment variables.
The server is multi-threaded, and access to SQLite is serialised with a lock.

## Test

```bash
python -m pytest            # add --cov=books_api if pytest-cov is installed
```

- `tests/test_api.py` calls the WSGI app in-process and covers every endpoint,
  the validation rules and the error codes.
- `tests/test_integration.py` starts a real HTTP server on a random port with a
  file-backed SQLite database. It runs the full CRUD cycle, checks that data
  persists to disk, and sends concurrent writes.

## API

A book has the following fields:

| Field    | Type    | Rules                                                              |
|----------|---------|--------------------------------------------------------------------|
| `id`     | integer | assigned by the server                                             |
| `title`  | string  | **required**, non-empty, at most 500 characters (trimmed)          |
| `author` | string  | **required**, non-empty, at most 500 characters (trimmed)          |
| `year`   | integer | optional, from -5000 to next year                                  |
| `isbn`   | string  | optional, ISBN-10 or ISBN-13; hyphens and spaces removed; unique   |

Fields not in this table are rejected.

| Method | Path          | Success          | Errors                  |
|--------|---------------|------------------|-------------------------|
| GET    | `/health`     | 200              | 503 if the DB is down   |
| POST   | `/books`      | 201 + `Location` | 400, 409 (duplicate ISBN) |
| GET    | `/books`      | 200 (array)      |                         |
| GET    | `/books/{id}` | 200              | 404                     |
| PUT    | `/books/{id}` | 200              | 400, 404, 409           |
| DELETE | `/books/{id}` | 204 (no body)    | 404                     |

- `GET /books?author=Frank%20Herbert` returns only books by that author. The match
  is exact but ignores case; an empty value is treated as no filter.
- `PUT` replaces the whole book, so `title` and `author` are required again.
  Leaving out `year` or `isbn` clears them.
- Unknown paths return 404. A wrong method returns 405 with an `Allow` header.
  A malformed JSON body returns 400, and a body over 1 MiB returns 413.

Errors are returned as JSON:

```json
{"error": "validation failed", "details": {"title": "title is required"}}
```

### Examples

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'
curl localhost:8000/books
curl 'localhost:8000/books?author=frank%20herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Layout

```
books_api/
  app.py         WSGI app: routing, JSON handling, status codes
  db.py          SQLite repository (thread-safe)
  validation.py  payload validation and normalisation
  __main__.py    threaded HTTP server / CLI entry point
tests/           pytest suite
```
