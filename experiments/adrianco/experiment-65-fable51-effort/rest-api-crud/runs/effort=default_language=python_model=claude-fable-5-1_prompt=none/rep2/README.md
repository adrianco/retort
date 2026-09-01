# Book Collection API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.10 or newer

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

The server listens on `http://0.0.0.0:5000`. Set `PORT` to change the port and
`BOOKS_DB_PATH` to change the SQLite file (default `books.db` in the working
directory). The database and table are created automatically on startup.

## Test

```bash
pytest
```

Tests run against a temporary SQLite database, so they never touch `books.db`.

## Endpoints

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | /health       | Health check, returns `{"status": "ok"}`     |
| POST   | /books        | Create a book                                |
| GET    | /books        | List books, optional `?author=` filter       |
| GET    | /books/{id}   | Get one book                                 |
| PUT    | /books/{id}   | Update a book (partial updates allowed)      |
| DELETE | /books/{id}   | Delete a book                                |

### Book fields

| Field  | Type    | Rules                                             |
|--------|---------|---------------------------------------------------|
| title  | string  | required, non-empty                               |
| author | string  | required, non-empty                               |
| year   | integer | optional, 0 to 9999                               |
| isbn   | string  | optional, 10 or 13 characters (hyphens allowed)   |

### Status codes

- `200` success, `201` created, `204` deleted
- `400` invalid JSON or validation failure (details in the `details` object)
- `404` book or route not found
- `405` method not allowed

### Examples

```bash
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:5000/books?author=Frank%20Herbert'

curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2019}'

curl -X DELETE localhost:5000/books/1
```
