# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

The service listens on http://127.0.0.1:8000. Interactive docs at `/docs`.

The SQLite file defaults to `books.db` in the working directory; override with the
`BOOKS_DB` environment variable. The table is created automatically at startup.

## Tests

```bash
pytest -q
```

Tests run against a temporary SQLite database (via the `BOOKS_DB` env var), so they
never touch your development data.

## Endpoints

| Method | Path           | Description                        | Success | Errors        |
| ------ | -------------- | ---------------------------------- | ------- | ------------- |
| GET    | `/health`      | Health check                       | 200     | —             |
| POST   | `/books`       | Create a book                      | 201     | 422           |
| GET    | `/books`       | List books, optional `?author=`    | 200     | —             |
| GET    | `/books/{id}`  | Fetch one book                     | 200     | 404           |
| PUT    | `/books/{id}`  | Replace a book                     | 200     | 404, 422      |
| DELETE | `/books/{id}`  | Delete a book                      | 204     | 404           |

### Book fields

- `title` — string, **required**, non-blank
- `author` — string, **required**, non-blank
- `year` — integer, optional, must be between 1 and 2200
- `isbn` — string, optional

Validation failures return `422` with FastAPI's standard error body.

## Examples

```bash
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```
