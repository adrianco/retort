# Book Collection API

A small REST API for managing a book collection, built with Python and SQLite.
The service uses only the standard library (WSGI via `wsgiref`); `pytest` is the only
dependency, needed just for the tests.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000`. Configuration via environment variables:

| Variable   | Default    | Purpose                   |
|------------|------------|---------------------------|
| `PORT`     | `5000`     | Port to listen on         |
| `BOOKS_DB` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                               | Success |
|--------|---------------|-------------------------------------------|---------|
| GET    | `/health`     | Health check                              | 200     |
| POST   | `/books`      | Create a book                             | 201     |
| GET    | `/books`      | List books (optional `?author=` filter)   | 200     |
| GET    | `/books/{id}` | Get one book                              | 200     |
| PUT    | `/books/{id}` | Replace a book                            | 200     |
| DELETE | `/books/{id}` | Delete a book                             | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

Validation rules:

- `title` and `author` are required, non-empty strings.
- `year` is optional and must be an integer.
- `isbn` is optional, must be a non-empty string, and must be unique.
- `PUT` replaces the whole book, so `title` and `author` are required there too;
  omitted optional fields are cleared.
- The `?author=` filter is an exact, case-insensitive match.

Errors are returned as JSON, e.g. `{"error": "validation failed", "details": [...]}`:
`400` for invalid input, `404` for an unknown book or path, `405` for an unsupported
method, `409` for a duplicate ISBN.

## Example

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl 'localhost:5000/books?author=Frank%20Herbert'
curl -X DELETE localhost:5000/books/1
```

## Tests

```bash
python -m pytest
```
