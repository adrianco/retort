# Book Collection API

A small REST API for managing books. It uses Flask and SQLite; the database is
created automatically on the first request.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

The server listens on `http://127.0.0.1:5000` by default and stores data in
`books.sqlite3` in the project directory. Set `BOOKS_DATABASE` to use a
different SQLite database file.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{ "status": "ok" }`. |
| `POST` | `/books` | Creates a book and returns it with HTTP `201`. |
| `GET` | `/books` | Returns all books. Use `?author=Name` to filter by exact author. |
| `GET` | `/books/{id}` | Returns one book or HTTP `404`. |
| `PUT` | `/books/{id}` | Replaces a book and returns the updated record. |
| `DELETE` | `/books/{id}` | Deletes a book and returns HTTP `204`. |

`POST` and `PUT` accept a JSON object with `title`, `author`, `year`, and
`isbn`. `title` and `author` are required, non-empty strings. `year` is an
optional integer and `isbn` is an optional string.

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"978-0807083697"}'
```

## Tests

```bash
python3 -m pytest
```
