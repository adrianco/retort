# Book Collection API

A REST API for managing books, written in Python using only the standard library
(`wsgiref` + `sqlite3`). No dependencies to install.

## Setup and run

Requires Python 3.8+.

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:8000`. Configure with environment variables:

| Variable   | Default     | Purpose              |
|------------|-------------|----------------------|
| `HOST`     | `127.0.0.1` | Bind address         |
| `PORT`     | `8000`      | Bind port            |
| `BOOKS_DB` | `books.db`  | SQLite database file |

## Endpoints

| Method | Path          | Description                                 | Success |
|--------|---------------|---------------------------------------------|---------|
| GET    | `/health`     | Health check                                | 200     |
| POST   | `/books`      | Create a book                               | 201     |
| GET    | `/books`      | List books; `?author=` filters (exact, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get one book                                | 200     |
| PUT    | `/books/{id}` | Replace a book (full update)                | 200     |
| DELETE | `/books/{id}` | Delete a book                               | 204     |

Book fields: `title` (required string), `author` (required string),
`year` (optional integer), `isbn` (optional string).

Errors are JSON: `{"error": "...", "details": {...}}` with status 400 (invalid
input), 404 (not found) or 405 (method not allowed).

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
python3 -m unittest -v
```
