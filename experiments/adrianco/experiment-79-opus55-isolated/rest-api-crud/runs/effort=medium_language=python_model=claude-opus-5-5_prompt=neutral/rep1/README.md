# Book Collection API

A small REST API for managing a book collection, backed by SQLite.

It uses only the Python standard library (`http.server` and `sqlite3`), so
there is nothing to install to run it. `pytest` is needed only for the tests.

## Setup

Requires Python 3.9 or newer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db`
in the current directory. Both can be changed with flags or environment
variables:

| Flag     | Environment variable | Default     |
|----------|----------------------|-------------|
| `--host` | `HOST`               | `127.0.0.1` |
| `--port` | `PORT`               | `8000`      |
| `--db`   | `BOOKS_DB`           | `books.db`  |

```bash
python app.py --port 9000 --db /tmp/books.db
```

## Test

```bash
python -m pytest
```

The tests start the real server on a free port with an in-memory database
and exercise it over HTTP.

## API

All request and response bodies are JSON.

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books, optionally `?author=`    | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

### Book fields

| Field    | Type    | Required | Notes                          |
|----------|---------|----------|--------------------------------|
| `title`  | string  | yes      | Must not be blank              |
| `author` | string  | yes      | Must not be blank              |
| `year`   | integer | no       | Between 0 and 9999             |
| `isbn`   | string  | no       |                                |

`id` is assigned by the server. Unknown fields in a request are ignored.

`PUT` replaces the whole book: `title` and `author` are required, and
optional fields left out of the request are reset to `null`.

The `?author=` filter matches the full author name, ignoring case.

### Errors

Errors are returned as `{"error": "<message>"}`. Validation failures also
include a `details` list with every problem found.

| Status | Meaning                                         |
|--------|-------------------------------------------------|
| 400    | Malformed JSON or failed validation             |
| 404    | Unknown route or no book with that id           |
| 405    | Method not supported on that route              |
| 413    | Request body larger than 1 MiB                  |

### Examples

```bash
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
# HTTP/1.0 201 Created
# {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}

curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'

curl -i -X DELETE http://127.0.0.1:8000/books/1

curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' -d '{"year": 1965}'
# {"error": "validation failed", "details": ["title is required", "author is required"]}
```
