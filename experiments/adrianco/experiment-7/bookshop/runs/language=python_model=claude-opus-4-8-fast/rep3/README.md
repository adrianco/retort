# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
standard-library **`sqlite3`** module.

## Requirements

- Python 3.9+

## Setup

```bash
python -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000`. The SQLite database is created
automatically as `books.db` in the project directory (override with the
`BOOKS_DB` environment variable, and the port with `PORT`).

You can also run it via Flask's CLI:

```bash
flask --app app run
```

## API

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check — returns `{"status":"ok"}` |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book                            |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'
```

List books by a specific author:

```bash
curl 'http://localhost:5000/books?author=Andrew%20Hunt'
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer, 20th Anniversary Edition","author":"Andrew Hunt","year":2019}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation error (e.g. missing `title`/`author`)
- `404 Not Found` — book does not exist

## Tests

```bash
pytest
```
