# Book Collection REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
python3 app.py
```

The server listens on `http://127.0.0.1:5000`; set the `PORT` environment
variable to use a different port (on macOS, AirPlay Receiver often occupies
5000). Data is stored in `books.db` (SQLite) in the working directory; override
the path with the `BOOKS_DB` environment variable.

## API

| Method | Path            | Description                              |
| ------ | --------------- | ---------------------------------------- |
| GET    | `/health`       | Health check — `{"status": "ok"}`        |
| POST   | `/books`        | Create a book (201, or 400 on bad input) |
| GET    | `/books`        | List books; supports `?author=` filter   |
| GET    | `/books/{id}`   | Get one book (404 if missing)            |
| PUT    | `/books/{id}`   | Update a book, partial updates allowed   |
| DELETE | `/books/{id}`   | Delete a book (204, 404 if missing)      |

A book looks like:

```json
{"id": 1, "title": "Release It!", "author": "Michael Nygard", "year": 2018, "isbn": "978-1680502398"}
```

`title` and `author` are required non-empty strings; `year` (integer) and
`isbn` (string) are optional. Validation errors return 400 with an `errors`
array.

### Examples

```sh
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
     -d '{"title": "Release It!", "author": "Michael Nygard", "year": 2018}'

curl 'localhost:5000/books?author=Michael%20Nygard'

curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
     -d '{"year": 2019}'

curl -X DELETE localhost:5000/books/1
```

## Tests

```sh
python3 -m pytest -v
```

Tests run against a temporary SQLite database per test, so they never touch
`books.db`.
