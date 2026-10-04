# Book Collection API

A REST API for managing books, written in Python using only the standard
library (`wsgiref` + `sqlite3`). No dependencies to install.

## Setup and run

Requires Python 3.8+.

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:8000`. Configure with environment variables:

| Variable   | Default     | Meaning                   |
|------------|-------------|---------------------------|
| `HOST`     | `127.0.0.1` | Bind address              |
| `PORT`     | `8000`      | Listen port               |
| `BOOKS_DB` | `books.db`  | SQLite database file path |

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional). `PUT` is a full
replacement, so `title` and `author` are required there too; omitted optional
fields are set to `null`. The `author` filter is an exact, case-insensitive match.

Errors are JSON, e.g. `{"error": "validation failed", "details": {"title": "..."}}`:
400 for invalid input or malformed JSON, 404 for unknown books or paths,
405 for unsupported methods.

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
python3 -m unittest -v
```

The tests start the API on a random local port with a temporary database.
