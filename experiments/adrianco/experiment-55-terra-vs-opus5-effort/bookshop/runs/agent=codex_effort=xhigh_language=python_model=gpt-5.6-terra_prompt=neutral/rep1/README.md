# Book Collection API

A small REST API for creating and managing books. It uses Flask and a local
SQLite database; no database server is needed.

## Setup and run

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The service listens on `http://127.0.0.1:5000`. By default, its database is
stored at `instance/books.sqlite3`. Set `BOOKS_DATABASE` to use another path.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status": "ok"}`. |
| `POST` | `/books` | Creates a book and returns it with status `201`. |
| `GET` | `/books` | Lists all books. Use `?author=Name` to filter by author. |
| `GET` | `/books/{id}` | Returns one book. |
| `PUT` | `/books/{id}` | Replaces a book. |
| `DELETE` | `/books/{id}` | Deletes a book and returns `204`. |

Create and update requests require JSON with non-empty `title` and `author`.
`year` is optional and must be an integer; `isbn` is optional and must be a
string. Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'
```

Missing resources return `404`, and invalid request data returns `400`. Error
responses are JSON objects containing an `error` message.

## Tests

```bash
python3 -m pytest -q
```
