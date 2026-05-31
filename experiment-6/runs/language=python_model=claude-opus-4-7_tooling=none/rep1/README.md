# Book Collection REST API

A minimal REST API for managing a book collection. Built with Python's standard library only — no external dependencies. Data is persisted in SQLite.

## Requirements

- Python 3.10 or newer (uses `from __future__ import annotations` and modern type hints)

## Setup and Run

No installation step is needed.

```bash
python3 app.py            # listens on http://127.0.0.1:8000
python3 app.py 9000       # custom port
```

The database file `books.db` is created in the working directory on first run.

## Endpoints

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check, returns `{"status": "ok"}` |
| POST   | `/books`       | Create a new book                        |
| GET    | `/books`       | List books, supports `?author=` filter   |
| GET    | `/books/{id}`  | Get a book by id                         |
| PUT    | `/books/{id}`  | Update a book (full or partial)          |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required strings. `year` is an optional integer; `isbn` is an optional string.

### Examples

```bash
# create
curl -s -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441172719"}'

# list, filtered
curl -s 'http://127.0.0.1:8000/books?author=Herbert'

# fetch
curl -s http://127.0.0.1:8000/books/1

# partial update
curl -s -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# delete
curl -i -X DELETE http://127.0.0.1:8000/books/1
```

### Status codes

- `200 OK` — successful read/update
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, missing required field, or bad id
- `404 Not Found` — unknown route or missing book

## Tests

```bash
python3 -m unittest test_app.py -v
```

Tests spin up the server on a random local port against a temporary SQLite database, exercising the full HTTP surface (health, CRUD, filtering, validation, and error paths).
