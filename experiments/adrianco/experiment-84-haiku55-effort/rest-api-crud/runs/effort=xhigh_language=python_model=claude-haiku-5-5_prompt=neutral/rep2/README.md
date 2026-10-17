# Books API

A REST service for managing a book collection. It uses only the Python standard
library (`http.server` and `sqlite3`), so there are no runtime dependencies.
pytest is needed only to run the tests.

Requires Python 3.10 or newer.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # pytest, for the test suite only
```

## Run

```bash
python -m bookapi                          # http://127.0.0.1:8000, data in ./books.db
python -m bookapi --port 9000 --db /tmp/books.db
```

| Option   | Environment variable | Default       |
|----------|----------------------|---------------|
| `--host` | `HOST`               | `127.0.0.1`   |
| `--port` | `PORT`               | `8000`        |
| `--db`   | `BOOKS_DB_PATH`      | `books.db`    |

The database file and table are created on first start. Stop the server with Ctrl+C.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`year` and `isbn` are optional. When omitted they are `null`.

| Method   | Path          | Success | Description |
|----------|---------------|---------|-------------|
| `POST`   | `/books`      | `201`   | Create a book. Body: `title` and `author` (required), `year` and `isbn` (optional). The response includes a `Location` header. |
| `GET`    | `/books`      | `200`   | List all books, ordered by id. `?author=` keeps books whose author contains the text, ignoring case. |
| `GET`    | `/books/{id}` | `200`   | Get one book. |
| `PUT`    | `/books/{id}` | `200`   | Replace a book. Takes the same body as `POST`, so omitted `year` and `isbn` are cleared. |
| `DELETE` | `/books/{id}` | `204`   | Delete a book. |
| `GET`    | `/health`     | `200`   | Health check. Returns `503` if the database cannot be reached. |

### Validation

- `title`, `author`: required, non-blank strings, at most 500 characters. Surrounding whitespace is trimmed.
- `year`: an integer from -3000 to next calendar year. Strings such as `"1965"` are rejected.
- `isbn`: an ISBN-10 or ISBN-13. Hyphens and spaces are allowed. The check digit is not verified.

### Errors

Every error body is JSON with an `error` field.

| Status | When |
|--------|------|
| `400`  | Validation failed. The body also has `details`, which maps each bad field to a message. Also returned for invalid JSON or a bad `Content-Length`. |
| `404`  | Unknown book id or unknown path. |
| `405`  | Method not supported on that path. The `Allow` header lists the valid methods. |
| `413`  | Request body larger than 1 MiB. |
| `500`  | Unexpected server error. Details are logged, not returned. |
| `503`  | `/health` only: database unavailable. |

Example validation failure:

```json
{"error": "Validation failed", "details": {"title": "is required", "year": "must be an integer"}}
```

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=herbert'

# Get, update, delete
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Tests

```bash
python -m pytest
```

The suite has three parts:

- `tests/test_validation.py`: validation rules, unit-tested.
- `tests/test_api.py`: every endpoint and error path, called directly with an in-memory database.
- `tests/test_server.py`: end-to-end requests over real HTTP on a free local port.

## Layout

```
bookapi/
  __main__.py   command-line entry point (python -m bookapi)
  server.py     HTTP transport built on http.server
  api.py        routing and status codes, independent of sockets
  validation.py input rules for book payloads
  db.py         SQLite storage
tests/          pytest suite
```

## Design notes

- **Storage:** a single SQLite connection is shared across request threads, and a lock serialises access to it. That is simple and correct for a service of this size.
- **Concurrency:** the server is threaded, so slow clients do not block others.
- **PUT semantics:** `PUT` replaces the whole book. Omitted optional fields are cleared rather than kept.
- **Duplicate ISBNs are allowed.** A collection can hold more than one copy of a book, so ISBN is not unique.
