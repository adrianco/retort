# Book Collection API

A small REST service for managing books, written with the Python standard library
(`http.server` + `sqlite3`). There are no third-party dependencies.

## Setup

Requires Python 3.9+. Nothing to install.

## Run

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db`.
Override with environment variables:

| Variable   | Default     | Purpose                   |
|------------|-------------|---------------------------|
| `HOST`     | `127.0.0.1` | Bind address              |
| `PORT`     | `8000`      | Listen port               |
| `BOOKS_DB` | `books.db`  | SQLite database file path |

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; `?author=` filters by author | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book fields:

- `title` — string, required
- `author` — string, required
- `year` — integer, optional
- `isbn` — string, optional, unique across books

`PUT` is a full replacement: `title` and `author` are required, and omitted optional
fields are cleared. The `author` filter is an exact, case-insensitive match.

Errors are JSON of the form `{"error": "..."}`:

| Status | Meaning                                                    |
|--------|------------------------------------------------------------|
| 400    | Body is not valid JSON                                     |
| 404    | Book or route not found                                    |
| 405    | Method not supported on that path                          |
| 409    | Another book already has that `isbn`                       |
| 422    | Validation failed; `details` maps each bad field to a reason |

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X DELETE localhost:8000/books/1
```

## Tests

```bash
python3 -m unittest -v
```

The tests start the real server on a free port against an in-memory database.
