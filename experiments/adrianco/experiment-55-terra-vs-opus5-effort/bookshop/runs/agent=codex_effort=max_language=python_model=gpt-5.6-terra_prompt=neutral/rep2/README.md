# Book Collection API

A small Flask REST API for creating, listing, reading, updating, and deleting books. Data is persisted in SQLite.

## Setup

Use Python 3.10 or newer, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the service

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000` and creates `books.sqlite3` in the project directory. To use another database location, set `BOOKS_DATABASE` before starting the application:

```bash
BOOKS_DATABASE=/tmp/my-books.sqlite3 python app.py
```

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check, returns `{"status":"ok"}` |
| `POST` | `/books` | Create a book; returns `201 Created` |
| `GET` | `/books` | List books; use `?author=Name` for a case-insensitive exact author filter |
| `GET` | `/books/{id}` | Read one book |
| `PUT` | `/books/{id}` | Fully replace a book |
| `DELETE` | `/books/{id}` | Delete a book; returns `204 No Content` |

`title` and `author` are required non-empty strings for both `POST` and `PUT`. `year` is optional and must be an integer from 0 to 9999; `isbn` is optional and may be a string or `null`.

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"978-0807083697"}'
```

## Tests

```bash
pytest
```

The test suite uses a temporary SQLite database and covers the health check, full CRUD lifecycle, author filtering, validation, and missing-book behavior.
