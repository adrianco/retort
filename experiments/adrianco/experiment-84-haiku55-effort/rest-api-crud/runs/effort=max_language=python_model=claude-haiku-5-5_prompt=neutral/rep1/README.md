# Book Collection API

A REST service for managing a book collection, with data stored in SQLite.
It uses only the Python standard library (`http.server`, `sqlite3`, `json`),
so there is nothing to install.

## Requirements

- Python 3.10 or newer

## Run

```bash
python server.py                              # http://127.0.0.1:8000, data in ./books.db
python server.py --port 9000 --db /tmp/b.db   # custom port and database file
```

| Option   | Default     | Meaning |
|----------|-------------|---------|
| `--host` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` to accept connections from other machines. |
| `--port` | `8000`      | Port to listen on. |
| `--db`   | `books.db`  | SQLite file. Created on first run, along with its table. |

## Test

```bash
python -m unittest -v     # standard library
python -m pytest          # if pytest is installed
```

Unit tests cover validation and storage. Integration tests start the real
server on a free port with a temporary database and call it over HTTP.

## API

Requests and responses are JSON. Errors have the shape `{"error": "..."}`.
Validation failures also include `details`, an object keyed by field name.

### Book

| Field    | Type    | Required | Rules |
|----------|---------|----------|-------|
| `id`     | integer | —        | Assigned by the server. Never reused after a delete. |
| `title`  | string  | yes      | Trimmed; not empty; at most 255 characters. |
| `author` | string  | yes      | Trimmed; not empty; at most 255 characters. |
| `year`   | integer | no       | Whole number from 1 to next calendar year. `null` if unknown. |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13. Hyphens and spaces are allowed. The check digit is not verified. `null` if unknown. |

Unrecognised fields in a request body are ignored, including any `id`.

### Endpoints

| Method   | Path          | Success | Possible errors |
|----------|---------------|---------|-----------------|
| `POST`   | `/books`      | `201 Created`, with a `Location` header and the new book | `400` invalid body, `413` body over 1 MiB, `415` wrong `Content-Type` |
| `GET`    | `/books`      | `200` array of books in id order. Optional `?author=` filter. | — |
| `GET`    | `/books/{id}` | `200` book | `404` |
| `PUT`    | `/books/{id}` | `200` updated book | `400` invalid body, `404`, `413`, `415` |
| `DELETE` | `/books/{id}` | `204 No Content` | `404` |
| `GET`    | `/health`     | `200 {"status": "ok"}` | `503` if the database is unreachable |

Other responses:

- `404` for unknown paths.
- `405` with an `Allow` header when the path exists but the method does not
  (for example `PATCH /books/1`).
- `501` for methods the server does not implement (for example `OPTIONS`).
- `500` for unexpected failures. The traceback is logged, not returned.

### Behaviour details

- **`POST` and `PUT` bodies** must be JSON objects, sent with
  `Content-Type: application/json` (a charset parameter is allowed). A missing
  `Content-Type` is accepted.
- **`PUT` is a partial update.** Only the fields you send change. The body must
  contain at least one known field. Sending `null` for `year` or `isbn` clears
  that field. `title` and `author` cannot be cleared.
- **`?author=` matches the full author name, ignoring case.** Use
  `?author=J.R.R. Tolkien`, not `?author=Tolkien`. An empty value returns all
  books.
- **Types are strict.** `"1937"` is not accepted for `year`, and `true` is not
  a number.

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "9780547928227"}'

# List, then filter by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=j.r.r.%20tolkien'

# Get one
curl http://127.0.0.1:8000/books/1

# Update the year only
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' -d '{"year": 1938}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

A validation failure returns `400` with the failing fields:

```json
{"error": "Validation failed", "details": {"title": "is required", "author": "is required"}}
```

## Project layout

| File                | Contents |
|---------------------|----------|
| `server.py`         | HTTP routing, request and response handling, and the `main()` entry point. |
| `store.py`          | SQLite storage. `BookStore` is safe to use from several threads. |
| `validation.py`     | Rules for book payloads. |
| `test_books_api.py` | Unit and integration tests. |
