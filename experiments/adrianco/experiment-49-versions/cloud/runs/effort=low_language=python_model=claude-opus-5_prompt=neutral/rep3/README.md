# Book Collection API

A small REST API for managing a book collection, built with **Python + Flask** and the
standard-library **sqlite3** module (no ORM, no external DB server).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

## Run

```bash
python3 app.py            # listens on http://127.0.0.1:5000
```

Environment variables:

| Variable   | Default            | Purpose                       |
|------------|--------------------|-------------------------------|
| `PORT`     | `5000`             | Port to bind                  |
| `BOOKS_DB` | `./books.db`       | SQLite database file location  |

The `books` table is created automatically on startup if it does not exist.

## Tests

```bash
python3 -m pytest -q
```

Tests use a temporary SQLite file per test (via `tmp_path`), so they never touch `books.db`.

## API

A book is JSON of the form:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn` (string)
are optional and default to `null`.

| Method   | Path           | Description                          | Success | Errors     |
|----------|----------------|--------------------------------------|---------|------------|
| `GET`    | `/health`      | Health check → `{"status":"ok"}`     | 200     | –          |
| `POST`   | `/books`       | Create a book                        | 201     | 400        |
| `GET`    | `/books`       | List books; `?author=` exact filter  | 200     | –          |
| `GET`    | `/books/{id}`  | Fetch one book                       | 200     | 404        |
| `PUT`    | `/books/{id}`  | Full update of a book                | 200     | 400, 404   |
| `DELETE` | `/books/{id}`  | Delete a book (empty body)           | 204     | 404        |

Validation failures return `{"errors": ["title is required", ...]}` with status 400;
missing resources return `{"error": "book not found"}` with status 404.

### Examples

```bash
curl -s localhost:5000/health

curl -s -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s 'localhost:5000/books?author=Frank%20Herbert'
curl -s localhost:5000/books/1

curl -s -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:5000/books/1   # 204
```
