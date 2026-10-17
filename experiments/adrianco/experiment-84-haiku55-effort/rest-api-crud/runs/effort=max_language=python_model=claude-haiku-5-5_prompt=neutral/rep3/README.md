# Book Collection API

A REST API for managing a book collection. It is built with [Flask](https://flask.palletsprojects.com/) and stores its data in SQLite through Python's built-in `sqlite3` module, so there is no database server to install.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

This installs the package in editable mode along with Flask and pytest.

## Run

```bash
flask --app bookapi run --port 8000
```

The server listens on `http://127.0.0.1:8000`. The example port avoids 5000, which macOS uses for AirPlay Receiver.

The database file defaults to `books.db` in the directory you start the server from. To use a different path, set `BOOKAPI_DATABASE`:

```bash
BOOKAPI_DATABASE=/var/lib/bookapi/books.db flask --app bookapi run --port 8000
```

The table is created on startup if it does not exist. Flask's development server is fine for local use. For deployment, run the app under a production WSGI server such as gunicorn or waitress.

## Test

```bash
pytest
```

The tests cover the HTTP endpoints (through Flask's test client, against a temporary SQLite file) and the validation rules on their own.

## API

Responses are JSON. Errors have the shape `{"error": "<message>"}`. Validation failures also include a `details` object that maps each invalid field to a message.

| Method   | Path          | Purpose                                          | Success                        | Failure      |
|----------|---------------|--------------------------------------------------|--------------------------------|--------------|
| `POST`   | `/books`      | Add a book                                       | `201` with a `Location` header | `400`        |
| `GET`    | `/books`      | List books, optionally filtered by `?author=`    | `200`                          | `400`        |
| `GET`    | `/books/{id}` | Get one book                                     | `200`                          | `404`        |
| `PUT`    | `/books/{id}` | Replace a book                                   | `200`                          | `400`, `404` |
| `DELETE` | `/books/{id}` | Delete a book                                    | `204`                          | `404`        |
| `GET`    | `/health`     | Check the service and its database               | `200`                          | `503`        |

Unknown routes and unsupported methods return `404` and `405` in the same JSON error shape.

### Book fields

| Field    | Type    | Required | Rules                                                                                                                                       |
|----------|---------|----------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `id`     | integer | —        | Assigned by the server. IDs are never reused after a delete.                                                                                |
| `title`  | string  | yes      | Not blank, at most 255 characters. Surrounding whitespace is trimmed.                                                                       |
| `author` | string  | yes      | Same rules as `title`.                                                                                                                      |
| `year`   | integer | no       | From 1 up to next calendar year, inclusive.                                                                                                 |
| `isbn`   | string  | no       | A valid ISBN-10 or ISBN-13, checked against its check digit. Hyphens and spaces are accepted; the stored value is digits only (ISBN-10 may end in `X`). |

### Examples

```bash
# Add a book
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-547-92822-7"}'

# List all books, or only one author's
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=J.R.R.%20Tolkien'

# Get, replace and delete a book
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937}'
curl -X DELETE http://127.0.0.1:8000/books/1

# Health check
curl http://127.0.0.1:8000/health
```

A request with missing required fields gets a `400`:

```json
{
  "error": "Validation failed",
  "details": {
    "author": "Author is required",
    "title": "Title is required"
  }
}
```

### Behaviour notes

- **`PUT` replaces the whole book.** Send `title` and `author`, plus `year` and `isbn` if you want to keep them. Optional fields you leave out are cleared.
- **The `author` filter is an exact match that ignores ASCII letter case.** `?author=orwell` does not match `George Orwell`. A blank filter gets a `400`.
- **Duplicates are allowed.** Nothing checks that an ISBN or title is unique, so the same book can be added more than once.
- **No pagination or authentication.** `GET /books` returns the whole collection, and anyone who can reach the server can change it.

## Project layout

```
bookapi/
  __init__.py       app factory and /health
  books.py          /books routes
  repository.py     SQL queries
  validation.py     field rules and ISBN check digits
  db.py             SQLite connection handling and schema
  errors.py         JSON error responses
tests/
  conftest.py           app and client fixtures
  test_books_api.py     HTTP-level tests
  test_validation.py    validation unit tests
pyproject.toml
```
