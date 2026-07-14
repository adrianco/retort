# Book Collection REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://0.0.0.0:5000` by default. Override with the
`PORT` environment variable. The SQLite file is `books.db` by default
(override with `BOOKS_DB`).

## Endpoints

| Method | Path           | Description                                  |
| ------ | -------------- | -------------------------------------------- |
| GET    | `/health`      | Health check, returns `{"status": "ok"}`     |
| POST   | `/books`       | Create a book (`title`, `author` required)   |
| GET    | `/books`       | List books, optional `?author=` filter       |
| GET    | `/books/{id}`  | Get a single book by ID                      |
| PUT    | `/books/{id}`  | Update a book (partial updates supported)    |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book schema

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780547928227"
}
```

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}'

curl http://localhost:5000/books?author=J.R.R.%20Tolkien
```

## Tests

```bash
pytest -v
```
