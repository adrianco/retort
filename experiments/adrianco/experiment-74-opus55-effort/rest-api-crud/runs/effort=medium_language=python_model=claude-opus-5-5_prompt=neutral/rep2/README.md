# Books API

A REST API for managing a book collection. It uses only the Python standard library (`http.server` and `sqlite3`), so the service itself has no third-party dependencies. You need pytest only to run the tests.

## Requirements

- Python 3.10+
- pytest (tests only)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python books_api.py
# Serving books API on http://127.0.0.1:8000 (db: books.db)
```

You can configure the service with these environment variables:

| Variable   | Default     | Meaning                    |
|------------|-------------|----------------------------|
| `HOST`     | `127.0.0.1` | Bind address               |
| `PORT`     | `8000`      | Port                       |
| `BOOKS_DB` | `books.db`  | Path to the SQLite file    |

## Endpoints

| Method | Path                  | Description                        | Success |
|--------|-----------------------|------------------------------------|---------|
| GET    | `/health`             | Health check (includes a DB ping)  | 200     |
| POST   | `/books`              | Create a book                      | 201     |
| GET    | `/books[?author=...]` | List books; the author filter ignores case | 200 |
| GET    | `/books/{id}`         | Get a book                         | 200     |
| PUT    | `/books/{id}`         | Replace a book                     | 200     |
| DELETE | `/books/{id}`         | Delete a book                      | 204     |

The request body for POST and PUT is JSON:

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

Validation rules:

- `title` and `author` are required and must be non-empty strings.
- `year` is optional. If present, it must be an integer.
- `isbn` is optional. If present, it must be a valid ISBN-10 or ISBN-13; hyphens and spaces are allowed.
- Unknown fields are rejected.

Error responses:

- `400`: the body is not valid JSON.
- `422`: validation failed. The response includes a `details` object that maps each bad field to its error.
- `404`: the book or route does not exist.
- `405`: the method is not supported on that path.

### Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
pytest -q
```

The tests start a real server on an ephemeral port with a temporary SQLite database. They cover:

- the full CRUD lifecycle
- the author filter
- required-field validation
- malformed JSON
- 404 and 405 handling
- data persistence across restarts
- unit tests of the validator and router
