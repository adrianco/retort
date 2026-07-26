# Book Collection API

A small REST API for managing a collection of books, built with **Flask** and
backed by **SQLite** (via the Python standard-library `sqlite3` module).

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service starts on `http://localhost:5000` and stores its data in a
`books.db` SQLite file created in the working directory.

## Run the tests

```bash
pytest
```

Tests use isolated temporary databases, so they do not touch `books.db`.

## API

All request and response bodies are JSON.

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check — returns `{"status":"ok"}` |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books; optional `?author=` filter   |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

| Field    | Type    | Required | Notes                    |
|----------|---------|----------|--------------------------|
| `title`  | string  | yes      | Must be non-empty        |
| `author` | string  | yes      | Must be non-empty        |
| `year`   | integer | no       |                          |
| `isbn`   | string  | no       |                          |

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'
```

List books by a given author:

```bash
curl 'http://localhost:5000/books?author=Andrew%20Hunt'
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2019}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — invalid or missing input
- `404 Not Found` — book does not exist
