# Book Collection API

A REST API for managing a book collection, written in Python using only the
standard library (`http.server` for HTTP, `sqlite3` for storage). The only
third-party dependency is `pytest`, needed to run the tests.

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python server.py
```

Environment variables (all optional):

| Variable        | Default      | Purpose                         |
|-----------------|--------------|---------------------------------|
| `HOST`          | `127.0.0.1`  | Interface to bind               |
| `PORT`          | `8000`       | Port to listen on               |
| `DATABASE_PATH` | `books.db`   | SQLite file (created on start)  |

## Test

```bash
pytest
```

## API

All requests and responses use JSON. Errors have the shape `{"error": "..."}`;
validation failures also include `"details"` mapping field names to messages.

| Method   | Path          | Description                                  | Success |
|----------|---------------|----------------------------------------------|---------|
| `GET`    | `/health`     | Health check                                 | 200     |
| `POST`   | `/books`      | Create a book                                | 201     |
| `GET`    | `/books`      | List books; optional `?author=` filter       | 200     |
| `GET`    | `/books/{id}` | Get one book                                 | 200     |
| `PUT`    | `/books/{id}` | Partially update a book                      | 200     |
| `DELETE` | `/books/{id}` | Delete a book                                | 204     |

### Book fields

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `id`     | integer | —        | Assigned by the server                 |
| `title`  | string  | yes      | Non-empty after trimming               |
| `author` | string  | yes      | Non-empty after trimming               |
| `year`   | integer | no       | 1–9999, or `null`                      |
| `isbn`   | string  | no       | Non-empty string, or `null`            |

### Behaviour notes

- **Create** requires `title` and `author`. Missing or blank values return `400`.
- **Update** is partial: only the fields you send are changed. Any title or
  author you send must still be non-empty.
- **List filter**: `?author=` matches the author case-insensitively and must
  be an exact match on the full name (not a substring).
- Malformed JSON or a non-object body returns `400`. Bodies over 1 MB return `413`.
- Non-numeric IDs such as `/books/abc` fall through to `404`.

### Examples

```bash
curl -i http://127.0.0.1:8000/health

curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl -i "http://127.0.0.1:8000/books?author=Frank%20Herbert"

curl -i -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

curl -i -X DELETE http://127.0.0.1:8000/books/1
```
