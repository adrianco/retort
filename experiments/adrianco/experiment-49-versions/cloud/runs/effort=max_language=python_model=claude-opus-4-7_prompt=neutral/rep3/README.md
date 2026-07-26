# Books REST API

A small Flask + SQLite REST service for managing a collection of books.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (`Flask`, `pytest`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://0.0.0.0:5000` by default. Override the port with
`PORT=8080 python3 app.py`, and the SQLite path with
`BOOKS_DB_PATH=/tmp/mybooks.db python3 app.py`. The schema is created
automatically on first boot.

## Test

```bash
python3 -m pytest -v
```

Each test uses a fresh temporary SQLite file so runs are isolated.

## Endpoints

| Method | Path                | Description                                      |
| ------ | ------------------- | ------------------------------------------------ |
| GET    | `/health`           | Health probe → `{"status": "ok"}`                |
| POST   | `/books`            | Create a book. Body: `title`, `author` required; `year`, `isbn` optional |
| GET    | `/books`            | List all books. Optional `?author=<name>` filter |
| GET    | `/books/<id>`       | Get a single book                                |
| PUT    | `/books/<id>`       | Update any subset of fields on a book            |
| DELETE | `/books/<id>`       | Delete a book                                    |

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (missing/invalid fields, unknown field, malformed JSON)
- `404 Not Found` — book id does not exist
- `405 Method Not Allowed` — wrong HTTP verb for a known path

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andy Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required non-empty strings. `year` is an optional
integer, `isbn` an optional string. Unknown fields are rejected.

## Example

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List, filtered by author
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

## Layout

- `app.py` — Flask application factory, routes, validation, SQLite setup
- `test_app.py` — pytest integration tests exercising every route
- `requirements.txt` — runtime + test dependencies
