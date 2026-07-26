# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via the Python standard-library `sqlite3` module).

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The server listens on `http://localhost:5000`. Data is persisted to
`books.db` in the working directory. Override the location with the
`BOOKS_DB_PATH` environment variable:

```bash
BOOKS_DB_PATH=/tmp/mybooks.db python app.py
```

## Running the tests

```bash
pytest -v
```

Tests run against a temporary database and do not touch `books.db`.

## API

All request and response bodies are JSON.

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`        |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book object

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are **required** and must be non-empty. `year`
(integer) and `isbn` (string) are optional.

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```

List books by a given author:

```bash
curl 'http://localhost:5000/books?author=Frank%20Herbert'
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## HTTP status codes

| Code | Meaning                                             |
|------|-----------------------------------------------------|
| 200  | OK (successful GET / PUT)                            |
| 201  | Created (successful POST)                            |
| 204  | No Content (successful DELETE)                       |
| 400  | Bad Request (invalid or missing fields, bad JSON)   |
| 404  | Not Found (no book with the given id)               |
