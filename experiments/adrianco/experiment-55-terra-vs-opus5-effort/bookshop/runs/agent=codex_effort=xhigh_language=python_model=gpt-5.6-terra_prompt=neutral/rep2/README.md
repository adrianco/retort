# Book Collection REST API

A Flask REST API that stores books in a local SQLite database.

## Setup and run

Requires Python 3.10 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The service listens on `http://127.0.0.1:5000` and creates `books.db` in the
current directory. Set `BOOKS_DATABASE` to choose another SQLite database path.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{ "status": "ok" }`. |
| `POST` | `/books` | Creates a book; `title` and `author` are required. |
| `GET` | `/books` | Lists books; use `?author=Name` to filter by exact author. |
| `GET` | `/books/{id}` | Gets one book. |
| `PUT` | `/books/{id}` | Updates any supplied book fields. |
| `DELETE` | `/books/{id}` | Deletes a book. |

All request bodies must be JSON. A book supports `title` and `author`
(non-empty strings), plus optional `year` (integer or `null`) and `isbn`
(string or `null`).

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"978-0807083697"}'
```

## Tests

```bash
python -m unittest -v
```
