# Book Collection API

A JSON REST API for managing a book collection, written in Python with SQLite storage.
It uses only the standard library at runtime (`wsgiref`, `sqlite3`, `json`). pytest is needed only to run the tests.

## Requirements

- Python 3.9 or newer

## Setup

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements-dev.txt   # pytest, for running the tests
```

## Run

```sh
python -m bookapi --port 8000 --db books.db
```

Options:

| Option   | Default                              | Description                              |
|----------|--------------------------------------|------------------------------------------|
| `--host` | `127.0.0.1`                          | Interface to bind                        |
| `--port` | `8000`                               | Port to listen on                        |
| `--db`   | `$BOOKS_DB_PATH` or `books.db`       | SQLite database file (created if absent) |

## Endpoints

| Method   | Path          | Success                | Description                                    |
|----------|---------------|------------------------|------------------------------------------------|
| `POST`   | `/books`      | `201 Created`          | Create a book. Sets a `Location` header.       |
| `GET`    | `/books`      | `200 OK`               | List books. Optional `?author=` filter.        |
| `GET`    | `/books/{id}` | `200 OK`               | Get one book.                                  |
| `PUT`    | `/books/{id}` | `200 OK`               | Replace a book's fields.                       |
| `DELETE` | `/books/{id}` | `204 No Content`       | Delete a book.                                 |
| `GET`    | `/health`     | `200 OK` / `503`       | Health check. Returns 503 if the database is unusable. |

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780306406157"}
```

Fields:

- `title` (string, required): trimmed, must not be blank, at most 500 characters.
- `author` (string, required): trimmed, must not be blank, at most 500 characters.
- `year` (integer, optional): between 1 and 9999.
- `isbn` (string, optional): ISBN-10 or ISBN-13. Hyphens and spaces are removed and the checksum is verified.
- `id` is assigned by the server. Any `id` in a request body is ignored.

`PUT` takes the full set of fields, validated the same way as `POST`. Omitted optional fields are cleared.

`GET /books?author=` matches the author exactly, ignoring case. An empty `author` value returns `400`.

### Examples

```sh
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-306-40615-7"}'

curl 'localhost:8000/books?author=frank%20herbert'

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

### Errors

Errors return JSON of the form `{"error": "..."}`.

| Status | When                                                                      |
|--------|---------------------------------------------------------------------------|
| `400`  | Malformed JSON, a non-object body, a failed validation, a non-integer id, or an empty author filter. Validation failures also include `details` with one message per field. |
| `404`  | Unknown book id, or unknown route.                                        |
| `405`  | Method not supported on that path. The `Allow` header lists the valid methods. |
| `413`  | Request body larger than 1 MB.                                            |
| `415`  | `POST` or `PUT` without `Content-Type: application/json`.                  |
| `500`  | Unexpected server error. Details are logged, not returned.                |

## Tests

```sh
python -m pytest
```

The suite has 46 tests in `tests/test_api.py`. Most call the WSGI app directly. One starts a real HTTP server and runs a full create, read, update, and delete cycle over the network. The persistence test checks that data survives reopening the database file.

## Layout

```
bookapi/
  app.py         WSGI application: routing, JSON parsing, error mapping
  store.py       SQLite storage layer
  validation.py  Payload validation (title, author, year, ISBN)
  server.py      Command-line entry point (wsgiref server)
  __main__.py    Enables `python -m bookapi`
tests/
  test_api.py    Endpoint, validation, and end-to-end tests
```
