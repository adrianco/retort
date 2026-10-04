# Book Collection API

A small JSON REST API for managing a book collection, stored in SQLite.

It is written in Python using only the standard library (`wsgiref` for HTTP,
`sqlite3` for storage), so there is nothing to install to run it. `pytest` is
needed only to run the tests.

## Requirements

- Python 3.10 or newer
- `pytest` (tests only)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest          # only needed for the tests
```

## Run

```bash
PYTHONPATH=src python -m bookapi
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db` in
the current directory (created on first start).

| Flag     | Environment variable | Default     | Meaning                                     |
|----------|----------------------|-------------|---------------------------------------------|
| `--host` | `BOOKS_HOST`         | `127.0.0.1` | Interface to bind (`0.0.0.0` for all)       |
| `--port` | `BOOKS_PORT`         | `8000`      | Port to listen on                           |
| `--db`   | `BOOKS_DB`           | `books.db`  | SQLite file (`:memory:` for a throwaway DB) |

Alternatively, `pip install -e .` installs a `bookapi` command that takes the
same flags and needs no `PYTHONPATH`.

`bookapi.BookAPI` is a standard WSGI application, so it can also be hosted by
any WSGI server (gunicorn, waitress, ...) in place of the built-in one. Use a
single process: the app serialises database access inside one process.

## Test

```bash
python -m pytest
```

The suite covers the API in-process (`tests/test_api.py`), the SQLite layer
(`tests/test_store.py`), and a full create/read/update/delete cycle over a real
HTTP socket (`tests/test_server.py`).

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
```

| Method   | Path          | Success          | Description                                   |
|----------|---------------|------------------|-----------------------------------------------|
| `GET`    | `/health`     | `200`            | Health check: `{"status": "ok"}`              |
| `POST`   | `/books`      | `201` + the book | Create a book; `Location` header has its URL  |
| `GET`    | `/books`      | `200` + array    | List all books, oldest first                  |
| `GET`    | `/books/{id}` | `200` + the book | Get one book                                  |
| `PUT`    | `/books/{id}` | `200` + the book | Replace a book                                |
| `DELETE` | `/books/{id}` | `204`, no body   | Delete a book                                 |

`GET /books?author=Frank%20Herbert` returns only that author's books. The match
is on the whole name and ignores ASCII case.

### Fields

| Field    | Rules                                                     |
|----------|-----------------------------------------------------------|
| `title`  | Required. Non-blank string, at most 500 characters.       |
| `author` | Required. Non-blank string, at most 500 characters.       |
| `year`   | Optional. Integer from 1 to 9999, or `null`.              |
| `isbn`   | Optional. String of at most 32 characters, or `null`.     |

Leading and trailing whitespace is trimmed. Unknown fields, including `id`, are
ignored. `PUT` replaces the whole book, so `title` and `author` must be sent
and an omitted `year` or `isbn` is reset to `null`.

### Errors

Every error has a JSON body with an `error` message. Validation errors also
list each offending field:

```json
{"error": "Validation failed", "details": {"title": "is required"}}
```

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| `400`  | Body is not valid JSON, or a field fails validation         |
| `404`  | Unknown path, or no book with that id                       |
| `405`  | Method not supported on that path (see the `Allow` header)  |
| `413`  | Request body larger than 1 MiB                              |
| `500`  | Unexpected server error (details go to the server log only) |
| `503`  | `/health` only: the database is not usable                  |

### Example

```bash
curl -i -X POST http://127.0.0.1:8000/books \
     -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl -i -X DELETE http://127.0.0.1:8000/books/1
```

## Design notes and limits

- **ISBNs are free text.** The format and checksum are not verified and two
  books may share an ISBN (for example two copies of one edition).
- **No pagination.** `GET /books` returns the whole collection.
- **No authentication.** The server binds to localhost by default; put it
  behind a reverse proxy that handles TLS and access control before exposing it.
- The built-in server is the standard library's threaded `wsgiref` server,
  which is fine for local and light use but is not hardened for the internet.

## Layout

```
src/bookapi/
    app.py          WSGI application: routing, status codes, JSON
    validation.py   Book payload validation
    store.py        SQLite persistence
    server.py       Command-line entry point and HTTP server
tests/              pytest suite
```
