# Books API

A minimal REST API for managing a book collection. Built with **Flask** and
**SQLite** using only the Python standard library plus Flask.

## Endpoints

| Method | Path            | Description                                                              |
|--------|-----------------|--------------------------------------------------------------------------|
| GET    | `/health`       | Health check. Returns `{"status": "ok"}` with HTTP 200.                  |
| POST   | `/books`        | Create a book. Body: `{title, author, year?, isbn?}`. Returns 201.       |
| GET    | `/books`        | List all books. Supports `?author=<name>` for exact-match filtering.     |
| GET    | `/books/{id}`   | Get a single book by ID. Returns 404 if not found.                       |
| PUT    | `/books/{id}`   | Replace a book. Body has same shape as POST. Returns 404 if not found.   |
| DELETE | `/books/{id}`   | Delete a book. Returns 204 on success, 404 if not found.                 |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required non-empty strings. `year` (integer) and
`isbn` (string) are optional and default to `null`.

### Errors

Validation and lookup errors return JSON of the form `{"error": "..."}` with
an appropriate HTTP status code (400 for bad input, 404 for missing
resource).

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on port `5000` by default. Override with `PORT`. Data is
written to `books.db` in the working directory; override with `BOOKS_DB`.

```bash
PORT=8080 BOOKS_DB=/tmp/books.db python3 app.py
```

## Try it

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl http://localhost:5000/books
curl 'http://localhost:5000/books?author=Frank%20Herbert'
curl http://localhost:5000/books/1

curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune (Deluxe Edition)", "author": "Frank Herbert", "year": 1965}'

curl -X DELETE http://localhost:5000/books/1
curl http://localhost:5000/health
```

## Tests

```bash
pytest -v
```

Tests use an isolated temporary SQLite database per test — they do not touch
`books.db`.
