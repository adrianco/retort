# Book API

A small REST API for managing a book collection. It is written in Python using
only the standard library (`wsgiref` + `sqlite3`), so there is nothing to
install to run it. Data is stored in a SQLite database file.

## Requirements

- Python 3.9 or newer
- `pytest` (only needed to run the tests)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # test dependencies only
```

## Run

```bash
python -m bookapi
```

The server listens on <http://127.0.0.1:8000> and stores data in `books.db` in
the current directory (created on first start).

| Option   | Environment variable | Default     | Description                     |
| -------- | -------------------- | ----------- | ------------------------------- |
| `--host` | `BOOKAPI_HOST`       | `127.0.0.1` | Address to bind                 |
| `--port` | `BOOKAPI_PORT`       | `8000`      | Port to listen on               |
| `--db`   | `BOOKAPI_DB`         | `books.db`  | Path to the SQLite database file |

```bash
python -m bookapi --host 0.0.0.0 --port 9000 --db /var/lib/books/books.db
```

The bundled server is the standard library's threaded WSGI server, which is
fine for local and light use. `bookapi.create_app(db_path)` returns a standard
WSGI application, so it can also be hosted by any WSGI server. Use a single
worker process with threads rather than multiple processes: the app serialises
database access through one connection per process.

## Test

```bash
pytest
```

The tests exercise the WSGI app in-process against an in-memory database, plus
an end-to-end run over a real socket and database file.

## API

All request and response bodies are JSON.

| Method   | Path          | Description                      | Success          |
| -------- | ------------- | -------------------------------- | ---------------- |
| `GET`    | `/health`     | Health check (verifies the database is reachable) | `200` |
| `POST`   | `/books`      | Create a book                    | `201` + `Location` header |
| `GET`    | `/books`      | List books, ordered by id        | `200`            |
| `GET`    | `/books/{id}` | Get one book                     | `200`            |
| `PUT`    | `/books/{id}` | Replace a book                   | `200`            |
| `DELETE` | `/books/{id}` | Delete a book                    | `204`, no body   |

### Book

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Field    | Type            | Rules                                                     |
| -------- | --------------- | --------------------------------------------------------- |
| `id`     | integer         | Assigned by the server; never reused after a delete       |
| `title`  | string          | **Required**, must not be blank                           |
| `author` | string          | **Required**, must not be blank                           |
| `year`   | integer or null | Optional, between -9999 and 9999                          |
| `isbn`   | string or null  | Optional; stored as given (no format or uniqueness check) |

Behaviour worth knowing:

- Leading and trailing whitespace is trimmed from `title`, `author` and `isbn`.
  A blank `isbn` is stored as `null`.
- Unknown fields in a request body (including `id`) are ignored.
- `PUT` replaces the whole book: `title` and `author` are required, and an
  omitted `year` or `isbn` is reset to `null`.
- `GET /books?author=` matches the author exactly (case-sensitive). An empty
  value returns all books.

### Errors

Errors are returned as `{"error": "<message>"}`. Validation failures add a
`details` object with one message per invalid field:

```json
{"error": "Validation failed", "details": {"title": "title is required", "year": "year must be an integer"}}
```

| Status | When                                                         |
| ------ | ------------------------------------------------------------ |
| `400`  | Body is not valid JSON, is not a JSON object, or fails validation |
| `404`  | Unknown path, or no book with that id                        |
| `405`  | Method not supported for the path (see the `Allow` header)   |
| `413`  | Request body larger than 1 MiB                               |
| `500`  | Unexpected server error                                      |
| `503`  | `/health` only: the database cannot be queried               |

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List, optionally filtered by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get, update, delete
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health check
curl http://127.0.0.1:8000/health
```

## Project layout

```
bookapi/
  app.py         WSGI application: routing, request parsing, responses
  store.py       SQLite persistence
  validation.py  Book payload validation
  __main__.py    Command-line entry point (python -m bookapi)
tests/
  conftest.py    In-process WSGI test client
  test_api.py    Endpoint behaviour
  test_server.py End-to-end over HTTP, concurrency, persistence
```
