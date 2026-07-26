# Book Collection API

A small REST service for managing a collection of books. Built with Flask and
backed by an embedded SQLite database.

## Requirements

- Python 3.10 or newer
- Flask 2.3+
- pytest 7.4+ (for running the tests)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the server

```bash
python3 app.py
```

The server listens on `0.0.0.0:5000` by default. Both the port and the
SQLite database file can be overridden with environment variables:

```bash
PORT=8080 DATABASE_PATH=/tmp/books.db python3 app.py
```

The schema is created automatically on start-up if it does not yet exist.

## Running the tests

```bash
python3 -m pytest -v
```

Each test uses its own temporary SQLite file, so the tests do not touch
your development database.

## API reference

All request and response bodies are JSON. Errors are returned as
`{"error": "...", "details": {...}}`.

| Method | Path                   | Description                                        |
| ------ | ---------------------- | -------------------------------------------------- |
| GET    | `/health`              | Liveness probe. Returns `{"status": "ok"}`.        |
| POST   | `/books`               | Create a book. Requires `title` and `author`.      |
| GET    | `/books`               | List books. Optional `?author=<name>` filter.      |
| GET    | `/books/<id>`          | Fetch one book by numeric id.                      |
| PUT    | `/books/<id>`          | Replace a book. Requires `title` and `author`.     |
| DELETE | `/books/<id>`          | Delete a book. Returns 204 on success.             |

### Book payload

| Field  | Type   | Required | Notes                              |
| ------ | ------ | -------- | ---------------------------------- |
| title  | string | yes      | Must be non-empty after trimming.  |
| author | string | yes      | Must be non-empty after trimming.  |
| year   | int    | no       | Integer year of publication.       |
| isbn   | string | no       | Free-form ISBN string.             |

### Status codes

- `200 OK` — successful read or update
- `201 Created` — new book created
- `204 No Content` — book deleted
- `400 Bad Request` — malformed JSON or validation error
- `404 Not Found` — no book with that id
- `405 Method Not Allowed` — HTTP method not supported for that path

## Example session

```bash
# create
curl -X POST http://localhost:5000/books \
    -H 'Content-Type: application/json' \
    -d '{"title":"1984","author":"Orwell","year":1949,"isbn":"9780451524935"}'
# → 201 {"id": 1, "title": "1984", ...}

# list
curl http://localhost:5000/books
# → 200 [{"id": 1, ...}]

# filter by author
curl 'http://localhost:5000/books?author=Orwell'

# fetch one
curl http://localhost:5000/books/1

# update
curl -X PUT http://localhost:5000/books/1 \
    -H 'Content-Type: application/json' \
    -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'

# delete
curl -X DELETE http://localhost:5000/books/1
# → 204
```
