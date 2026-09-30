# Book Collection API

A small REST API for managing a book collection, written in Python with
**no runtime dependencies**: a WSGI application served by the standard library's
`wsgiref`, with data stored in SQLite (`sqlite3`).

No web framework was specified for this project, so the standard library was used
rather than adding a dependency.

## Setup

Developed and tested on Python 3.14; it should work on 3.9+ but that has not been verified.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt     # only needed to run the tests (pytest, pytest-cov)
```

## Run

```bash
PYTHONPATH=src python -m bookapi                  # http://127.0.0.1:8000, db in ./books.db
PYTHONPATH=src python -m bookapi --port 9000 --db /tmp/my-books.db
```

| Option   | Environment variable | Default     |
|----------|----------------------|-------------|
| `--host` | `HOST`               | `127.0.0.1` |
| `--port` | `PORT`               | `8000`      |
| `--db`   | `BOOKS_DB`           | `books.db`  |

The database file and its table are created on first start. Stop the server with Ctrl-C.

The server is a threaded `wsgiref` server, which is fine for development and small
deployments. `bookapi.app.BookApp` is a plain WSGI callable, so it can also be
served by any WSGI server (e.g. `BookApp(BookStore("books.db"))`).

## Test

```bash
python -m pytest
python -m pytest --cov=bookapi --cov-report=term-missing
```

`pyproject.toml` puts `src/` on the import path, so no install step is needed.
The tests cover the API in-process, the storage layer, input validation, a real HTTP
server on a loopback socket (including concurrent requests), and the `python -m bookapi`
entry point.

## API

All responses are JSON (except `204 No Content`). Errors look like:

```json
{"error": "validation failed", "details": {"author": "author is required"}}
```

A book:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method   | Path          | Description                          | Success |
|----------|---------------|--------------------------------------|---------|
| `GET`    | `/health`     | Health check (verifies the database) | `200`   |
| `POST`   | `/books`      | Create a book                        | `201`   |
| `GET`    | `/books`      | List books, optional `?author=`      | `200`   |
| `GET`    | `/books/{id}` | Get one book                         | `200`   |
| `PUT`    | `/books/{id}` | Update a book                        | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`   |

### Fields and validation

| Field    | Type    | Rules                                                   |
|----------|---------|---------------------------------------------------------|
| `title`  | string  | **required**, not blank, max 500 characters (trimmed)   |
| `author` | string  | **required**, not blank, max 500 characters (trimmed)   |
| `year`   | integer | optional, 0–9999 (`null` allowed)                       |
| `isbn`   | string  | optional, max 32 characters; not format-checked or unique |

Unknown fields (including `id`) are ignored. Validation failures return `400` with a
`details` object naming every invalid field.

### Behaviour notes

- **`GET /books?author=`** matches the author name exactly, ignoring case and
  surrounding whitespace. An empty `author=` means no filter. Results are ordered by id.
- **`PUT /books/{id}`** updates the fields you send and leaves the others unchanged;
  send `null` for `year` or `isbn` to clear them. `title` and `author` can be changed
  but never blanked. A body with no known fields is a `400`.
- **`POST /books`** returns `201` with a `Location: /books/{id}` header.
- IDs are never reused after a delete.
- Status codes: `400` invalid JSON / validation / bad `Content-Length`, `404` unknown
  book or path (a non-numeric id is just an unknown book), `405` wrong method (with an
  `Allow` header), `413` body over 1 MiB, `500` unexpected error (details are logged,
  not returned), `503` from `/health` if the database is unusable.
- A trailing slash is accepted (`/books/` and `/books`).

### Example

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl 'localhost:8000/books?author=frank%20herbert'
curl -X PUT localhost:8000/books/1 -d '{"year": 1966}'
curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Layout

```
src/bookapi/
  app.py         WSGI app: routing, request parsing, JSON responses
  validation.py  payload validation
  db.py          SQLite repository (thread-safe)
  server.py      threaded wsgiref server
  __main__.py    CLI entry point
tests/           pytest suite
```
