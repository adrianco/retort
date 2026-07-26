# Book API

A small REST API for managing a book collection, written in Python with
[Flask](https://flask.palletsprojects.com/) and backed by SQLite (from the
standard library — there is no ORM and no database server to install).

* JSON in, JSON out — including every error response.
* Validation with field-level error messages.
* Filtering, full-text-ish search, sorting and pagination on the collection.
* 152 tests covering the endpoints, validation and the storage layer.

## Requirements

* Python 3.9 or newer
* Flask 2.2+ (`pip install -r requirements.txt`)

SQLite ships with Python, so no other service is required.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m book_api                 # http://127.0.0.1:8000
```

Useful options:

```bash
python -m book_api --port 9000 --host 0.0.0.0
python -m book_api --database :memory:   # throwaway database, nothing on disk
python -m book_api --debug               # auto-reload while developing
```

Other entry points, all serving the same app:

```bash
flask --app wsgi run --port 8000    # Flask CLI
```

`wsgi.py` also exposes a plain WSGI callable, so any production server can host
it once you have installed one (they are deliberately not in
`requirements.txt`):

```bash
pip install gunicorn && gunicorn wsgi:app
pip install waitress && waitress-serve --port 8000 wsgi:app
```

The database file (`books.db` by default) and its schema are created
automatically on first start.

## Quick tour

```bash
curl localhost:8000/health

curl -X POST localhost:8000/books \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## API reference

| Method   | Path           | Description                     | Success        |
| -------- | -------------- | ------------------------------- | -------------- |
| `GET`    | `/health`      | Service and database health     | `200`, `503`   |
| `GET`    | `/`            | Self-describing endpoint index  | `200`          |
| `POST`   | `/books`       | Create a book                   | `201`          |
| `GET`    | `/books`       | List books (filter/sort/page)   | `200`          |
| `GET`    | `/books/{id}`  | Fetch one book                  | `200`          |
| `PUT`    | `/books/{id}`  | Replace a book                  | `200`          |
| `PATCH`  | `/books/{id}`  | Update selected fields          | `200`          |
| `DELETE` | `/books/{id}`  | Delete a book                   | `204`          |

### The book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-01359-3",
  "created_at": "2024-05-01T09:12:44.512Z",
  "updated_at": "2024-05-01T09:12:44.512Z"
}
```

| Field    | Type            | Rules                                                                     |
| -------- | --------------- | ------------------------------------------------------------------------- |
| `title`  | string          | **Required**, non-blank after trimming, ≤ 512 characters                  |
| `author` | string          | **Required**, non-blank after trimming, ≤ 256 characters                  |
| `year`   | integer or null | Optional; between 1 and next year. `"1965"` and `1965.0` are coerced      |
| `isbn`   | string or null  | Optional; ISBN-10 or ISBN-13 (10 digits with an optional `X` check digit, or 13 digits), hyphens/spaces optional; unique across the collection |

`id`, `created_at` and `updated_at` are server-generated. Unknown fields in a
payload are ignored, so a book read from the API can be sent straight back to
`PUT` after editing.

### `POST /books`

Responds `201` with the created book and a `Location` header pointing at it.

```http
POST /books
{"title": "Dune", "author": "Frank Herbert", "year": 1965}

201 Created
Location: /books/1
```

### `GET /books`

Returns a JSON **array**; the total number of matching books is in the
`X-Total-Count` header (and `X-Limit`/`X-Offset` when paginating).

| Parameter | Meaning                                                                           |
| --------- | --------------------------------------------------------------------------------- |
| `author`  | Case-insensitive **exact** match on the author name                               |
| `year`    | Exact match on the publication year                                               |
| `q`       | Case-insensitive **substring** search over title and author                       |
| `sort`    | `id`, `title`, `author`, `year`, `created_at`, `updated_at`; prefix `-` to reverse |
| `limit`   | 1–500; omitted means "no limit", so `GET /books` really does list every book      |
| `offset`  | Number of books to skip (default 0)                                               |

```bash
curl 'localhost:8000/books?author=Frank%20Herbert&sort=-year&limit=10&offset=0'
```

Blank values (`?author=`) are treated as "not supplied"; unknown parameters are
ignored.

### `PUT` vs `PATCH`

`PUT` replaces the whole resource: `title` and `author` are required, and any
optional field you leave out is cleared to `null`. `PATCH` only touches the
fields present in the payload, so `{"year": 2005}` changes nothing else. Both
return `404` when the id does not exist — `PUT` never creates a book, because
ids are assigned by the server.

### Errors

Every error — including 404s from unrouted URLs and 405s — is JSON with the
same shape:

```json
{
  "error": "validation_error",
  "message": "The request payload failed validation.",
  "details": {
    "title": "This field is required.",
    "year": "Must be an integer."
  }
}
```

`details` is present only when there is field-level information, and it lists
**all** offending fields at once rather than stopping at the first one.

| Status | `error`                | When                                                     |
| ------ | ---------------------- | -------------------------------------------------------- |
| `400`  | `validation_error`     | Malformed JSON, bad payload or bad query parameter        |
| `404`  | `not_found`            | Unknown book id or unknown URL                            |
| `405`  | `method_not_allowed`   | Wrong HTTP method (the `Allow` header lists the right ones) |
| `409`  | `conflict`             | The ISBN already belongs to another book                  |
| `413`  | `content_too_large`    | The request body is larger than 1 MiB                     |
| `500`  | `internal_error`       | Unexpected server-side failure (details are logged, not returned) |
| `503`  | *(health payload)*     | `GET /health` could not reach the database                |

## Configuration

All settings are optional environment variables:

| Variable                 | Default    | Purpose                                                     |
| ------------------------ | ---------- | ----------------------------------------------------------- |
| `BOOK_API_DATABASE`      | `books.db` | SQLite file, or `:memory:` for an ephemeral database         |
| `BOOK_API_MAX_PAGE_SIZE` | `500`      | Largest accepted `?limit=`                                   |
| `BOOK_API_STRICT_ISBN`   | `false`    | Also verify the ISBN **check digit**, not just its shape     |
| `BOOK_API_SQLITE_TIMEOUT`| `5.0`      | Seconds to wait for a locked database                        |
| `BOOK_API_MAX_CONTENT_LENGTH` | `1048576` | Largest accepted request body, in bytes                 |
| `BOOK_API_HOST` / `BOOK_API_PORT` | `127.0.0.1` / `8000` | Defaults for `python -m book_api`         |

## Tests

```bash
python -m pytest            # 152 tests
python -m pytest -v         # verbose
```

The suite runs against a private in-memory database and needs no setup. It
covers:

| File                          | Focus                                                            |
| ----------------------------- | ---------------------------------------------------------------- |
| `tests/test_health.py`        | Health payload, book count, database-down behaviour              |
| `tests/test_create_book.py`   | `POST` happy paths, `Location`, optional fields, ISBN conflicts   |
| `tests/test_list_books.py`    | Listing, `?author=` filter, search, sorting, pagination headers   |
| `tests/test_get_update_delete.py` | `GET`/`PUT`/`PATCH`/`DELETE` semantics and their 404s        |
| `tests/test_validation.py`    | Required fields, type/range rules, ISBN helpers, query validation |
| `tests/test_errors.py`        | JSON 404/405/500 responses                                        |
| `tests/test_storage.py`       | Persistence across restarts, per-request connections, concurrency, SQL injection |

## Project layout

```
book_api/
  __init__.py      application factory and configuration
  __main__.py      "python -m book_api" development server
  db.py            SQLite connections, schema, per-request lifecycle
  models.py        the Book dataclass and its JSON representation
  repository.py    every SQL statement, all values bound as parameters
  validators.py    request body and query-string validation
  routes.py        the HTTP endpoints
  errors.py        error types and the JSON error handlers
  utils.py         timestamp helpers
tests/             pytest suite
wsgi.py            entry point for gunicorn/waitress/flask run
```

## Design notes

* **Application factory.** `create_app()` takes a config override, which is how
  the tests get an isolated database without touching the environment.
* **One connection per request.** Connections live in Flask's application
  context and are closed on teardown, so the app is safe under threaded servers.
  File databases use WAL journalling so readers do not block the writer.
* **`:memory:` really is shared.** A plain in-memory SQLite database is private
  to a single connection, so `db.py` maps `:memory:` to a uniquely named
  shared-cache URI and holds one connection open for the lifetime of the app.
  Shared-cache SQLite locks whole tables and answers a collision with
  `SQLITE_LOCKED`, which the busy handler never retries — so in-memory requests
  take turns on that one connection under a lock instead of opening their own
  and failing. File databases keep a connection per request.
* **Untrusted text is checked before it reaches the driver.** Null bytes,
  unpaired surrogates (legal in JSON, unstorable in SQLite), non-ASCII digits
  masquerading as ISBNs, and integers too large for SQLite — or for CPython's
  `int()` — are all rejected as `400`s rather than becoming `500`s.
* **ISBNs are stored twice.** The value the client sent is returned verbatim,
  while a normalised copy (digits only) carries the unique index — so
  `978-0-441-01359-3` and `9780441013593` are correctly recognised as the same
  edition. The index is partial, so any number of books may have no ISBN.
* **Shape before checksum.** ISBN check-digit validation is real but opt-in
  (`BOOK_API_STRICT_ISBN=1`), because plenty of catalogues contain
  well-formed-but-wrong ISBNs and rejecting them by default is surprising.
* **Lenient about `Content-Type`.** A body that parses as JSON is accepted even
  when the header is missing or wrong, which makes `curl -d '...'` work as
  people expect; a body that is not valid JSON is still a `400`.
* **Arrays stay arrays.** `GET /books` returns a bare JSON array and puts the
  pagination metadata in headers, so clients never have to unwrap an envelope.
