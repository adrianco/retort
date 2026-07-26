# Book Collection API

A small REST API for managing a collection of books, built with **Flask** and
backed by **SQLite** (via Python's standard-library `sqlite3` module — no ORM,
no external database).

## Features

- Full CRUD for books (`title`, `author`, `year`, `isbn`)
- List with an optional `?author=` filter (case-insensitive)
- Input validation — `title` and `author` are required
- JSON responses with appropriate HTTP status codes
- Health-check endpoint

## Requirements

- Python 3.8+
- Flask (see [`requirements.txt`](requirements.txt))

## Setup

```bash
# (optional) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` by default. Override the host,
port, or database location with environment variables:

```bash
HOST=0.0.0.0 PORT=5000 BOOKS_DB_PATH=/data/books.db python app.py
```

Alternative launchers:

```bash
flask --app app run --port 8000     # Flask CLI (auto-detects the create_app factory)
gunicorn wsgi:app                   # production WSGI server
```

The SQLite database file (default `books.db`) is created automatically on first
run.

## API reference

Base URL: `http://127.0.0.1:8000`

| Method   | Path           | Description                          | Success |
| -------- | -------------- | ------------------------------------ | ------- |
| `GET`    | `/health`      | Health check                         | `200`   |
| `POST`   | `/books`       | Create a book                        | `201`   |
| `GET`    | `/books`       | List books (`?author=` to filter)    | `200`   |
| `GET`    | `/books/{id}`  | Get one book                         | `200`   |
| `PUT`    | `/books/{id}`  | Replace/update a book                | `200`   |
| `DELETE` | `/books/{id}`  | Delete a book                        | `200`   |

### Book object

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0261102217"
}
```

### Validation rules

| Field    | Required | Type    | Notes                                |
| -------- | -------- | ------- | ------------------------------------ |
| `title`  | yes      | string  | Must be non-empty (whitespace trimmed) |
| `author` | yes      | string  | Must be non-empty (whitespace trimmed) |
| `year`   | no       | integer | Optional; must be an integer if given  |
| `isbn`   | no       | string  | Optional; must be a string if given    |

Invalid input returns `400` with a JSON body:

```json
{
  "error": "Validation failed",
  "details": ["title is required and must be a non-empty string"]
}
```

A request for a book that does not exist returns `404`:

```json
{ "error": "Book 42 not found" }
```

> **Note on `PUT`:** it performs a *full replacement* of the resource. Fields
> not supplied (`year`, `isbn`) are reset to `null`. `title` and `author`
> remain required.

### Examples

Create a book:

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0261102217"}'
```

List all books / filter by author:

```bash
curl http://127.0.0.1:8000/books
curl "http://127.0.0.1:8000/books?author=J.R.R.%20Tolkien"
```

Get, update, and delete a book:

```bash
curl http://127.0.0.1:8000/books/1

curl -X PUT http://127.0.0.1:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1951}'

curl -X DELETE http://127.0.0.1:8000/books/1
```

## Running the tests

```bash
pip install -r requirements.txt
pytest -v
```

The test suite (`test_app.py`) covers the health check, CRUD operations, the
author filter, validation failures, and error handling. Each test runs against
its own temporary SQLite database, so tests are isolated and leave no artifacts.

## Project structure

```
.
├── app.py            # Application factory, routes, DB + validation helpers
├── wsgi.py           # WSGI entrypoint for gunicorn/uWSGI
├── test_app.py       # pytest integration tests
├── requirements.txt  # Python dependencies
└── README.md
```
