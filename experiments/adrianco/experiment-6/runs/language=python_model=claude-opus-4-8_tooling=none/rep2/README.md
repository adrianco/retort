# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via Python's standard-library `sqlite3` module).

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python3 app.py
```

The server starts on `http://localhost:5000`. The SQLite database file
(`books.db` by default) is created automatically on first run. You can
override its location with the `BOOKS_DB` environment variable and the port
with `PORT`.

## Running the tests

```bash
pytest
```

Tests use an isolated temporary database, so they never touch your real data.

## API

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check — returns `{"status":"ok"}` |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book fields

- `title` *(string, required)*
- `author` *(string, required)*
- `year` *(integer, optional)*
- `isbn` *(string, optional)*

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Pragmatic Programmer", "author": "Hunt", "year": 1999, "isbn": "978-0201616224"}'
```

List books by a given author:

```bash
curl "http://localhost:5000/books?author=Hunt"
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 2019}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Responses & status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST (returns the created book)
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (missing/blank `title` or `author`, bad types)
- `404 Not Found` — book ID does not exist

All non-empty responses are JSON. Errors are returned as `{"error": "..."}`.
