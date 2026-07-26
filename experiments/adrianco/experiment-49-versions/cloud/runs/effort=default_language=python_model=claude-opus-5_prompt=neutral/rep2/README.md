# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and **SQLite**
(via the standard-library `sqlite3` module — no ORM, no external database).

## Requirements

- Python 3.10+ (developed and tested on 3.14)
- The dependencies in `requirements.txt` (FastAPI, Uvicorn, Pydantic v2)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn bookapi.main:app --reload           # http://127.0.0.1:8000
```

or

```bash
python -m bookapi.main                      # honours $HOST and $PORT
```

The database file is created automatically on startup. It defaults to `books.db` in the
working directory; set `BOOKS_DB_PATH` to put it somewhere else:

```bash
BOOKS_DB_PATH=/var/lib/books/books.db uvicorn bookapi.main:app
```

Interactive API docs are served at <http://127.0.0.1:8000/docs> (OpenAPI schema at
`/openapi.json`).

## Test

```bash
pytest
```

60 tests cover the endpoints end-to-end (through the ASGI stack with a temporary SQLite
file per test), the validation rules, and the storage layer.

## API

| Method   | Path          | Success        | Description                                  |
| -------- | ------------- | -------------- | -------------------------------------------- |
| `GET`    | `/health`     | `200`          | Liveness plus a database check               |
| `POST`   | `/books`      | `201`          | Create a book (`Location` header on success) |
| `GET`    | `/books`      | `200`          | List all books, optional `?author=` filter   |
| `GET`    | `/books/{id}` | `200`          | Fetch one book                               |
| `PUT`    | `/books/{id}` | `200`          | Replace a book                               |
| `DELETE` | `/books/{id}` | `204`          | Delete a book                                |

### Book fields

| Field        | Type            | Notes                                                        |
| ------------ | --------------- | ------------------------------------------------------------ |
| `id`         | integer         | Assigned by the server                                       |
| `title`      | string          | **Required**, 1–500 characters after trimming                |
| `author`     | string          | **Required**, 1–255 characters after trimming                |
| `year`       | integer \| null | Optional, 1–2100                                             |
| `isbn`       | string \| null  | Optional, ISBN-10 or ISBN-13; unique across the collection   |
| `created_at` | string          | UTC ISO-8601 timestamp                                       |
| `updated_at` | string          | UTC ISO-8601 timestamp                                       |

Notes:

- `title` and `author` are trimmed; a whitespace-only value is rejected.
- `isbn` is normalised — spaces and hyphens are stripped and a trailing `x` is upper-cased,
  so `978-0441013593` is stored and returned as `9780441013593`.
- Unknown fields in the request body are rejected rather than silently ignored.
- `PUT` is a **full replacement**: optional fields you omit are cleared to `null`.
- The `?author=` filter is an exact, case-insensitive match on the whole author name.
  `?author=` with an empty value returns everything.

### Status codes

| Code  | When                                                                |
| ----- | ------------------------------------------------------------------- |
| `200` | Successful `GET` / `PUT`                                            |
| `201` | Book created                                                        |
| `204` | Book deleted (empty body)                                           |
| `400` | Validation failure — missing/blank `title` or `author`, bad `year`, malformed ISBN, unparseable JSON, non-numeric id |
| `404` | No book with that id (or unknown route)                             |
| `409` | The supplied ISBN already belongs to another book                   |
| `503` | The database is unreachable (health check only)                     |

### Error format

Every non-2xx response has the same shape:

```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [{ "field": "title", "message": "Field required" }]
}
```

`details` is empty for errors that are not field-specific (e.g. `404`).

## Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
# HTTP/1.1 201 Created
# location: /books/1
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593", ...}

# List, and filter by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=frank%20herbert'

# Read one
curl http://127.0.0.1:8000/books/1

# Replace
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (revised)","author":"Frank Herbert","year":1990}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1     # 204 No Content

# Health
curl http://127.0.0.1:8000/health                   # {"status":"ok","database":"ok"}
```

## Layout

```
bookapi/
  app.py          FastAPI application factory: routes and error handlers
  db.py           SQLite connection helpers and schema
  repository.py   CRUD queries against the books table
  schemas.py      Pydantic request/response models and validation rules
  main.py         ASGI entry point (uvicorn bookapi.main:app)
tests/
  conftest.py     Fixtures: a fresh app + temporary database per test
  test_books_api.py   Endpoint behaviour (CRUD, filtering, status codes)
  test_validation.py  Input validation and error responses
  test_storage.py     Persistence, configuration and the repository layer
```

## Design notes

- **One connection per request.** `get_conn` is a FastAPI dependency that opens a
  connection and closes it when the response is finished, so handlers can stay
  synchronous (FastAPI runs `def` endpoints in a worker thread) without sharing a
  connection across threads. WAL mode is enabled so reads do not block on a writer.
- **Application factory.** `create_app(db_path)` builds an app bound to a specific
  database file, which is what lets each test run against its own throwaway file.
- **Validation lives in Pydantic models**, so the same rules apply to `POST` and `PUT`
  and are reflected in the generated OpenAPI schema.
- **Validation failures return `400`** rather than FastAPI's default `422`; the
  `RequestValidationError` handler also reshapes the body into the common error format.
