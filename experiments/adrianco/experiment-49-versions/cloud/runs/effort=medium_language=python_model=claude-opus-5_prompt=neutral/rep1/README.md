# Book Collection API

A small REST service for managing a book collection, built with **FastAPI** and backed by
**SQLite** (via the Python standard library's `sqlite3` — no ORM).

## Requirements

- Python 3.10+
- The dependencies in `requirements.txt`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn bookapi.main:app --reload --port 8000
```

The service creates its SQLite file on startup. By default that is `books.db` in the
working directory; set `BOOKS_DB_PATH` to put it elsewhere:

```bash
BOOKS_DB_PATH=/var/lib/books/books.db uvicorn bookapi.main:app --port 8000
```

Interactive API docs are served at <http://127.0.0.1:8000/docs>.

## Tests

```bash
pytest
```

The suite (36 tests) runs against a temporary SQLite database created per test, so it
never touches your development data.

## API

Base URL in the examples below: `http://127.0.0.1:8000`

| Method   | Path          | Description                        | Success |
| -------- | ------------- | ---------------------------------- | ------- |
| `GET`    | `/health`     | Health check (also pings the DB)   | 200     |
| `POST`   | `/books`      | Create a book                      | 201     |
| `GET`    | `/books`      | List books, optional `?author=`    | 200     |
| `GET`    | `/books/{id}` | Fetch one book                     | 200     |
| `PUT`    | `/books/{id}` | Replace a book                     | 200     |
| `DELETE` | `/books/{id}` | Delete a book                      | 204     |

### Book object

| Field    | Type              | Required | Notes                                            |
| -------- | ----------------- | -------- | ------------------------------------------------ |
| `id`     | integer           | —        | Server-assigned                                  |
| `title`  | string            | **yes**  | Non-blank, ≤ 500 chars, whitespace-trimmed       |
| `author` | string            | **yes**  | Non-blank, ≤ 300 chars, whitespace-trimmed       |
| `year`   | integer \| `null` | no       | Between 1450 and five years from now             |
| `isbn`   | string \| `null`  | no       | 10 or 13 chars ignoring hyphens/spaces; unique   |

### Status codes

| Code  | When                                                              |
| ----- | ----------------------------------------------------------------- |
| `200` | Successful `GET` / `PUT`                                          |
| `201` | Book created — the `Location` header points at the new resource   |
| `204` | Book deleted (empty body)                                         |
| `404` | No book with that id                                              |
| `409` | Another book already uses that `isbn`                             |
| `422` | Validation failure — body lists the offending fields              |
| `503` | Database unreachable (from `/health`)                             |

### Examples

Create:

```bash
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```
HTTP/1.1 201 Created
location: /books/1

{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593","id":1}
```

List, filtered by author (exact match):

```bash
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
```

Update — `PUT` is a full replacement, so any optional field you omit is cleared:

```bash
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

Delete:

```bash
curl -i -X DELETE http://127.0.0.1:8000/books/1   # 204 No Content
```

A validation failure returns a 422 naming the field:

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' -d '{"author":"No Title"}'
```

```json
{"detail":[{"type":"missing","loc":["body","title"],"msg":"Field required"}]}
```

## Layout

```
bookapi/
  main.py      # FastAPI app: routes, status codes, error translation
  schemas.py   # Pydantic models and validation rules
  db.py        # SQLite connection handling and schema
tests/
  conftest.py          # per-test temporary database fixture
  test_books_api.py    # CRUD, filtering, health check
  test_validation.py   # required fields, year/ISBN rules
```

## Design notes

- **No ORM.** The data model is a single table, so parameterised `sqlite3` queries are
  clearer than a dependency on SQLAlchemy. All queries bind parameters, so there is no
  SQL-injection surface.
- **`isbn` is `UNIQUE`.** An ISBN identifies an edition, so a duplicate is a client error
  (`409`) rather than a silently accepted second row. An empty-string `isbn` is coerced
  to `NULL` so multiple books without an ISBN don't collide.
- **Unknown fields are rejected** (`extra="forbid"`) so a typo like `{"titel": ...}`
  fails loudly instead of quietly creating an untitled book.
- **`PUT` replaces** the whole resource, matching HTTP semantics. There is no `PATCH`
  endpoint; the task did not call for partial updates.
