# Book Collection API

A small REST API for managing a collection of books, built with
**Flask** and **SQLite** (via Python's standard-library `sqlite3` module —
no external database server required).

## Requirements

- Python 3.9+
- Flask (see `requirements.txt`)

## Setup

```bash
# (optional) create an isolated environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on <http://localhost:5000>. Configuration is via
environment variables:

| Variable   | Default    | Description                          |
| ---------- | ---------- | ------------------------------------ |
| `PORT`     | `5000`     | Port to listen on                    |
| `BOOKS_DB` | `books.db` | Path to the SQLite database file     |

The SQLite file (and the `books` table) is created automatically on first
run.

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are **required**; `year` (integer) and `isbn` (string)
are optional.

| Method   | Path            | Description                              | Success | Errors     |
| -------- | --------------- | ---------------------------------------- | ------- | ---------- |
| `GET`    | `/health`       | Liveness + DB connectivity check         | `200`   | `500`      |
| `POST`   | `/books`        | Create a book                            | `201`   | `400`      |
| `GET`    | `/books`        | List books (optional `?author=` filter)  | `200`   | –          |
| `GET`    | `/books/<id>`   | Fetch a single book                      | `200`   | `404`      |
| `PUT`    | `/books/<id>`   | Replace a book (full update)             | `200`   | `400`,`404`|
| `DELETE` | `/books/<id>`   | Delete a book                            | `200`   | `404`      |

Notes:

- The `?author=` filter is an exact, **case-insensitive** match.
- `PUT` performs a full replacement, so `title` and `author` are required
  just like on create.
- Validation failures return `{"errors": [...]}`; not-found returns
  `{"error": "..."}`. Unknown routes and wrong methods also return JSON.

### Examples

```bash
# Health check
curl localhost:5000/health

# Create
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'

# List everything / filter by author
curl localhost:5000/books
curl 'localhost:5000/books?author=Frank%20Herbert'

# Fetch one
curl localhost:5000/books/1

# Update
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete
curl -X DELETE localhost:5000/books/1
```

## Tests

The test suite uses `pytest`. Each test runs against a throwaway SQLite file
(under pytest's `tmp_path`), so it never touches your real `books.db`.

```bash
pip install -r requirements.txt
pytest -v
```

## Project layout

```
app.py            # Flask application (factory + routes + SQLite access)
test_app.py       # pytest integration tests
requirements.txt  # dependencies
README.md         # this file
```
