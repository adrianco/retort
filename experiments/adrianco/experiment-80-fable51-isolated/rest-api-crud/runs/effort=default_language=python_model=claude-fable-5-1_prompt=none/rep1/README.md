# Book Collection API

A small REST API for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so there is nothing to install to
run it. Data is stored in a SQLite database file.

## Requirements

- Python 3.9+
- `pytest` (tests only)

## Run

```bash
python3 app.py                       # http://127.0.0.1:8000, data in ./books.db
python3 app.py --host 0.0.0.0 --port 9000 --db /path/to/books.db
```

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

- `title` and `author` are required, non-empty strings.
- `year` (integer) and `isbn` (string) are optional and default to `null`.
- `PUT` is a full replacement, so it takes the same body as `POST`.
- The `?author=` filter is an exact, case-insensitive match.

Errors are JSON: `{"error": "...", "details": [...]}` with status `400`
(invalid JSON or failed validation), `404` (unknown book or route), `405`
(unsupported method) or `413` (body over 1 MB).

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
python3 -m pip install -r requirements-dev.txt   # pytest
python3 -m pytest
```

The tests start the real server on an ephemeral port with a temporary database.
