# Book Collection API

A small REST API for managing a collection of books, built with **Flask** and
backed by **SQLite**. It provides full CRUD, an author filter, input
validation, and a health check — with JSON responses and appropriate HTTP
status codes throughout.

## Requirements

- Python 3.8+
- [Flask](https://flask.palletsprojects.com/) (see `requirements.txt`)

## Setup

```bash
# (optional) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install runtime dependencies
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

This starts the development server on <http://127.0.0.1:5000>. By default the
database is written to `books.db` in the current directory. Override the
location with the `BOOKS_DB` environment variable:

```bash
BOOKS_DB=/tmp/mybooks.db python app.py
```

Alternatively, run through the Flask CLI (it auto-detects the `create_app`
factory):

```bash
flask --app app run
```

## Data model

A book has the following fields:

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `id`     | integer | —        | Assigned by the server                 |
| `title`  | string  | **yes**  | Non-empty                              |
| `author` | string  | **yes**  | Non-empty                              |
| `year`   | integer | no       | 0–9999; defaults to `null`             |
| `isbn`   | string  | no       | Defaults to `null`                     |

## API reference

All request and response bodies are JSON. Send `Content-Type: application/json`
on requests with a body.

| Method   | Path            | Description                          | Success |
|----------|-----------------|--------------------------------------|---------|
| `GET`    | `/health`       | Service + database health check      | `200`   |
| `POST`   | `/books`        | Create a book                        | `201`   |
| `GET`    | `/books`        | List books (optional `?author=`)     | `200`   |
| `GET`    | `/books/{id}`   | Fetch a single book                  | `200`   |
| `PUT`    | `/books/{id}`   | Replace a book                       | `200`   |
| `DELETE` | `/books/{id}`   | Delete a book                        | `204`   |

### Status codes

- `200 OK` — successful read/update/list
- `201 Created` — book created
- `204 No Content` — book deleted (empty body)
- `400 Bad Request` — invalid/missing JSON body or failed validation
- `404 Not Found` — unknown book id or route
- `405 Method Not Allowed` — unsupported method for a route

### Notes on behavior

- **`PUT` is a full replace.** `title` and `author` are required; any omitted
  optional field (`year`, `isbn`) is reset to `null`.
- **The `?author=` filter is an exact, case-insensitive match**, so
  `?author=tolkien` matches a book whose author is `Tolkien`.
- Validation failures return a helpful list of messages:
  `{"error": "Validation failed", "details": ["title is required ..."]}`.

## Example requests

```bash
# Health check
curl http://127.0.0.1:5000/health

# Create a book
curl -X POST http://127.0.0.1:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'

# List all books
curl http://127.0.0.1:5000/books

# Filter by author
curl "http://127.0.0.1:5000/books?author=Frank%20Herbert"

# Get one book
curl http://127.0.0.1:5000/books/1

# Update a book
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete a book
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite (`test_app.py`) contains 33 unit and integration tests covering the
full CRUD lifecycle, the author filter, validation rules, error handling, and
the health check. Each test runs against an isolated temporary SQLite database,
so tests never touch your real data.

## Project layout

```
.
├── app.py                 # Flask application (factory + routes)
├── test_app.py            # pytest unit + integration tests
├── requirements.txt       # runtime dependencies
├── requirements-dev.txt   # test dependencies
└── README.md
```
