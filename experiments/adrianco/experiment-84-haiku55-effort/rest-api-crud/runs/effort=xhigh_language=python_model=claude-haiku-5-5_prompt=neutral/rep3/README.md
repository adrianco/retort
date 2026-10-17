# Book Collection API

A REST API for managing a book collection. Data is stored in SQLite, and API
responses are JSON. It uses only the Python standard library at runtime.

## Requirements

- Python 3.13 (the version it was tested with)
- pytest, for running the tests (listed in `requirements-dev.txt`)

## Setup

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```sh
python -m bookapi                          # http://127.0.0.1:8000, database ./books.db
python -m bookapi --port 9000 --db /tmp/books.db
```

Options:

| Option   | Default                                  | Description                       |
| -------- | ---------------------------------------- | --------------------------------- |
| `--host` | `127.0.0.1`                              | Interface to bind                 |
| `--port` | `8000`                                   | Port to listen on                 |
| `--db`   | `$BOOKS_DB_PATH` or `books.db`           | SQLite database file              |

Stop the server with Ctrl+C. The database file and its tables are created on first start.

## Endpoints

A book has the shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required. `year` (an integer) and `isbn` are optional and
may be `null`.

| Method   | Path          | Success                         | Errors                                   |
| -------- | ------------- | ------------------------------- | ---------------------------------------- |
| `POST`   | `/books`      | `201` with the book and `Location` | `400` validation failed                |
| `GET`    | `/books`      | `200` with an array of books    |                                          |
| `GET`    | `/books?author=NAME` | `200` books by that author (case-insensitive exact match) | `400` empty filter |
| `GET`    | `/books/{id}` | `200` with the book             | `404` not found                          |
| `PUT`    | `/books/{id}` | `200` with the updated book     | `400` validation failed, `404` not found |
| `DELETE` | `/books/{id}` | `204` with no body              | `404` not found                          |
| `GET`    | `/health`     | `200` `{"status": "ok"}`        | `503` database unavailable               |

Other errors:

- `400` for a malformed or non-object JSON body.
- `404` for an unknown path.
- `405` for an unsupported method on a known path, with an `Allow` header.
- `413` for a body over 64 KiB.
- `501` for `Transfer-Encoding` request bodies (send `Content-Length` instead).

Validation errors list every bad field at once:

```json
{"error": "Validation failed", "details": {"title": "must not be blank", "author": "is required"}}
```

### Validation rules

- `title` and `author`: strings, at least one non-space character after trimming, at most 500 characters.
- `year`: an integer from -3000 to next calendar year. JSON booleans and strings are rejected.
- `isbn`: a valid ISBN-10 or ISBN-13 with a correct check digit. Hyphens and spaces
  are accepted and stored as bare digits (`978-0-441-17271-9` becomes `9780441172719`).

### PUT semantics

`PUT` replaces the whole book. Send `title` and `author` every time. Any omitted
`year` or `isbn` is cleared to `null`.

## Examples

```sh
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl "http://127.0.0.1:8000/books?author=frank%20herbert"
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -i -X DELETE http://127.0.0.1:8000/books/1
curl http://127.0.0.1:8000/health
```

## Tests

```sh
python -m pytest
```

The suite has 93 tests in four groups:

- `tests/test_validation.py`: field rules and ISBN checksums.
- `tests/test_repository.py`: SQLite storage, including persistence across reopening.
- `tests/test_api.py`: every endpoint and error path, called in-process without a socket.
- `tests/test_http.py`, `tests/test_cli.py`: real HTTP requests to a running server, a
  concurrent-write check, and a start-up and shutdown of `python -m bookapi`.

## Layout

```
bookapi/
  __main__.py     command-line entry point
  api.py          routing and handlers; transport-independent
  server.py       http.server adapter
  repository.py   SQLite storage
  validation.py   input validation
  models.py       Book and BookFields dataclasses
tests/            pytest suite
pytest.ini
requirements-dev.txt
```

## Design notes

- **Standard library only.** `http.server` and `sqlite3` need no install, so the
  service runs on any stock Python 3.13 install.
- **Shared connection.** One SQLite connection serves all request threads, with every
  query behind a lock. This keeps the server simple, and it suits a small collection.
  It would not scale to heavy write load.
- **Case-insensitive author filter.** SQLite's `NOCASE` folds ASCII letters only, so
  `ÉMILE` will not match `émile`.
