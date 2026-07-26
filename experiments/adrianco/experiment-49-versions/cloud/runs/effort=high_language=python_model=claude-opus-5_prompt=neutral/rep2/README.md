# Book Collection API

A small REST service for managing a collection of books, built with
**FastAPI** and **SQLite** (via the standard-library `sqlite3` module — no ORM).

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The service listens on <http://127.0.0.1:8000>. `python main.py` also works and
starts the same app without reload.

The SQLite file is created automatically on startup. It defaults to `books.db`
in the working directory; set `BOOKS_DB_PATH` to put it elsewhere:

```bash
BOOKS_DB_PATH=/var/lib/books/books.db uvicorn main:app
```

Interactive API docs (generated from the code) are at
<http://127.0.0.1:8000/docs>, and the OpenAPI schema at `/openapi.json`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

70 tests covering every endpoint end-to-end (`test_api.py`) plus the
persistence layer and validation rules (`test_database.py`). Each test runs
against its own temporary database, so the suite never touches `books.db`.

## API

| Method   | Path          | Description                    | Success |
| -------- | ------------- | ------------------------------ | ------- |
| `GET`    | `/health`     | Service + database health      | 200     |
| `POST`   | `/books`      | Create a book                  | 201     |
| `GET`    | `/books`      | List books (`?author=` filter) | 200     |
| `GET`    | `/books/{id}` | Fetch one book                 | 200     |
| `PUT`    | `/books/{id}` | Replace a book                 | 200     |
| `PATCH`  | `/books/{id}` | Update selected fields         | 200     |
| `DELETE` | `/books/{id}` | Delete a book                  | 204     |

### Book resource

```json
{
  "id": 1,
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "9780441478125"
}
```

`title` and `author` are required; `year` and `isbn` are optional and may be
`null`.

### Status codes

| Code | When                                                              |
| ---- | ----------------------------------------------------------------- |
| 200  | Successful read or update                                          |
| 201  | Book created (a `Location` header points at the new resource)      |
| 204  | Book deleted (empty body)                                          |
| 400  | Invalid input — missing/blank `title` or `author`, bad `year`/`isbn`, malformed JSON, bad query or path parameter |
| 404  | No book with that id (also returned for unknown routes)            |
| 409  | The supplied `isbn` already belongs to another book                |
| 503  | The database is unreachable (`/health` only)                       |

Every error uses the same JSON shape:

```json
{ "detail": "Book with id 42 not found" }
```

Validation failures add a per-field breakdown:

```json
{
  "detail": "Validation failed",
  "errors": [{ "field": "title", "message": "Field required", "type": "missing" }]
}
```

### Validation rules

- `title` and `author` are trimmed of surrounding whitespace and must be
  non-empty (max 500 / 300 characters). `"   "` is rejected.
- `year`, when supplied, must be an integer between 1000 and next year
  (forthcoming titles are allowed).
- `isbn`, when supplied, must be an ISBN-10 (9 digits + digit or `X`) or an
  ISBN-13 (13 digits). Hyphens and spaces are allowed and stripped before
  storage, so `978-0-441-47812-5` and `9780441478125` are the same ISBN.
  Format only — check digits are not verified. A blank string is treated as
  "not provided".
- ISBNs are unique across the collection; books without an ISBN never collide.

## Examples

```bash
# Create
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'
# -> 201  {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}

# List, and filter by author
curl localhost:8000/books
curl 'localhost:8000/books?author=herbert'

# Paginate
curl 'localhost:8000/books?limit=10&offset=20'

# Read / replace / patch / delete
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X PATCH localhost:8000/books/1 \
  -H 'Content-Type: application/json' -d '{"year":1969}'
curl -X DELETE localhost:8000/books/1     # -> 204

# Health
curl localhost:8000/health
# -> {"status":"ok","database":"ok","version":"1.0.0"}
```

## Design notes

**Layout** — three small modules, each with one job:

| File               | Role                                                            |
| ------------------ | --------------------------------------------------------------- |
| `main.py`          | FastAPI app: routes, status codes, error handlers                |
| `models.py`        | Pydantic request/response schemas and all validation rules       |
| `database.py`      | SQLite schema, connections, and CRUD queries                     |
| `conftest.py`      | Test fixtures (temporary database per test)                      |

**Filtering** — `?author=` is a case-insensitive *substring* match, so
`?author=le guin` finds "Ursula K. Le Guin". User input is escaped, so a `%` or
`_` in the query is matched literally rather than acting as a SQL wildcard.
`limit` (1–1000) and `offset` are optional; with neither, all books are
returned.

**PUT vs PATCH** — `PUT` replaces the resource, so omitting `year` or `isbn`
clears them. `PATCH` only touches the fields you send; sending `"year": null`
clears that one field, while `"title": null` is rejected.

**Connections** — a fresh SQLite connection is opened per request via a FastAPI
dependency and closed afterwards. That keeps things safe when FastAPI runs sync
endpoints on its worker thread pool, and avoids sharing a connection across
threads. Writes commit immediately; a failed write leaves the row untouched.

**SQL injection** — every query uses bound parameters; no SQL is built from
user input beyond a fixed whitelist of column names in the `PATCH` update.

**Trade-offs** — for a single-file embedded database at this scale, plain
`sqlite3` is clearer and lighter than an ORM. If the collection grew to need
authorship tables, migrations, or a networked database, SQLAlchemy plus Alembic
would be the next step. SQLite's `lower()` is ASCII-only, so the author filter
is case-insensitive for ASCII names only.

Verified with Python 3.14, FastAPI 0.140, pydantic 2.13, uvicorn, pytest 9.
