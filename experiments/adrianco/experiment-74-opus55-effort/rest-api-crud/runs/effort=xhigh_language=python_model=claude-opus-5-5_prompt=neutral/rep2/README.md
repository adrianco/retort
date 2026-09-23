# Books API

A REST API for managing a book collection. It stores data in SQLite and returns JSON.

The service uses only the Python standard library (`http.server`, `sqlite3`, `json`),
so it has **no runtime dependencies**. You need pytest only to run the tests.

## Requirements

- Python 3.10 or newer (tested on 3.10, 3.12 and 3.14)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install pytest                # only needed for running the tests
```

You can also install it as a package, which adds a `books-api` command:

```bash
pip install -e ".[test]"
```

## Running

```bash
python -m books_api                          # http://127.0.0.1:8000, data in ./books.db
python -m books_api --host 0.0.0.0 --port 9000 --db /var/lib/books/books.db
python -m books_api --db :memory:            # throwaway in-memory database
```

| Option   | Environment variable | Default     | Notes                                       |
|----------|----------------------|-------------|---------------------------------------------|
| `--host` | `BOOKS_API_HOST`     | `127.0.0.1` | Use `0.0.0.0` to listen on all interfaces   |
| `--port` | `BOOKS_API_PORT`     | `8000`      | `0` picks a free port (printed at startup)  |
| `--db`   | `BOOKS_DB_PATH`      | `books.db`  | SQLite file; parent directories are created |

The database schema is created automatically on first start. Stop the server with
Ctrl+C or `SIGTERM`.

## API

### Book

```json
{"id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0-452-28423-4"}
```

| Field    | Type            | Rules                                                                    |
|----------|-----------------|--------------------------------------------------------------------------|
| `id`     | integer         | Assigned by the server. Ignored if sent. Never reused after a delete     |
| `title`  | string          | **Required**, non-blank, at most 500 characters; whitespace is trimmed    |
| `author` | string          | **Required**, non-blank, at most 300 characters; whitespace is trimmed    |
| `year`   | integer or null | Optional; between -9999 and the current year                             |
| `isbn`   | string or null  | Optional; ISBN-10 or ISBN-13 digits, single hyphens or spaces allowed (check digit not verified); stored as sent |

Unknown fields are ignored.

### Endpoints

| Method   | Path          | Success                                   | Errors        |
|----------|---------------|-------------------------------------------|---------------|
| `GET`    | `/health`     | `200` `{"status": "ok", "database": "ok"}`  | `503` if the database is unusable |
| `POST`   | `/books`      | `201` with the created book and a `Location` header | `400` |
| `GET`    | `/books`      | `200` with an array of books ordered by id | |
| `GET`    | `/books?author=orwell` | `200` with books whose author contains the text, ignoring case | |
| `GET`    | `/books/{id}` | `200` with the book                        | `404` |
| `PUT`    | `/books/{id}` | `200` with the updated book                | `400`, `404` |
| `DELETE` | `/books/{id}` | `204` with no body                         | `404` |

**Updating (`PUT`)**: send the full book, or only the fields you want to change.
Fields you leave out keep their current values. To clear `year` or `isbn`, set it to
`null`. `title` and `author` can't be cleared. A body with none of the known fields
returns `400`.

**Filtering**: `?author=` matches any part of the author's name and ignores case,
including non-ASCII letters: `?author=GÜNTER` finds "Günter Grass". An empty value
returns every book.

### Errors

Every error returns a JSON body with an `error` message. Validation errors also list
each invalid field:

```json
{"error": "Validation failed", "details": {"title": "title is required", "year": "year must be an integer"}}
```

| Status | When |
|--------|------|
| `400`  | Invalid JSON, a body that isn't a JSON object, or a failed validation |
| `404`  | Unknown route, or no book with that id (including ids that aren't integers) |
| `405`  | Method not supported on that path; the `Allow` header lists the valid ones |
| `408` / `411` / `413` | Body not received in 30 s / chunked body without `Content-Length` / body over 1 MiB |
| `500`  | Unexpected server error (the details go to the log, not the response) |

### Examples

```bash
curl -i -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0-452-28423-4"}'
curl localhost:8000/books
curl 'localhost:8000/books?author=orwell'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' -d '{"year": 1950}'
curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Tests

```bash
python -m pytest
```

The suite has 138 tests and runs in about a second:

| File                        | Covers |
|-----------------------------|--------|
| `tests/test_validation.py`  | Field rules: required fields, types, trimming, year range, ISBN format, partial updates |
| `tests/test_repository.py`  | SQLite CRUD, the author filter (case, Unicode, literal `%`/`_`), persistence to a file, concurrent writes |
| `tests/test_api.py`         | Every endpoint and status code, called through `BooksApp.handle` with no socket |
| `tests/test_server.py`      | Real HTTP: a CRUD round trip, keep-alive framing, HEAD, 408/411/413/501, concurrent clients, and `python -m books_api` persisting data across a restart |

## Project layout

```
books_api/
  validation.py   payload validation and normalisation
  db.py           BookRepository: SQLite storage
  app.py          BooksApp: routing, JSON and status codes (no HTTP server code)
  server.py       http.server transport and the command-line entry point
  __main__.py     `python -m books_api`
tests/            pytest suite
```

## Design notes

- **Standard library only.** No framework was specified. `http.server` plus `sqlite3`
  covers this API, and the service runs on any Python 3.10+ without installing anything.
- **Transport kept separate from logic.** `BooksApp.handle(method, target, body)`
  returns a `Response`, so routing and validation are tested without sockets, and
  `server.py` is a thin adapter. Moving to WSGI/ASGI would mean replacing only that
  adapter.
- **Concurrency.** The server handles each connection on its own thread. All threads
  share one SQLite connection behind a lock. That makes writes safe and lets
  `:memory:` work, since each new `:memory:` connection would open a separate empty
  database. For a small service like this, serialising database access costs little.
- **SQL safety.** Every value is passed as a query parameter. The one dynamic
  statement, the `UPDATE ... SET` clause, only uses column names from a fixed
  whitelist.
