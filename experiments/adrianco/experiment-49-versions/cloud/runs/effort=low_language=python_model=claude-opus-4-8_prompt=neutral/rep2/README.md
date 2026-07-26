# Book Collection API

A REST API service for managing a book collection, built with Flask and SQLite.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server starts on `http://localhost:5000`. Data is stored in a local
SQLite file (`books.db`), created automatically on first run.

## Endpoints

| Method | Path            | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/health`       | Health check                         |
| POST   | `/books`        | Create a book                        |
| GET    | `/books`        | List books (optional `?author=` filter) |
| GET    | `/books/{id}`   | Get a single book                    |
| PUT    | `/books/{id}`   | Update a book                        |
| DELETE | `/books/{id}`   | Delete a book                        |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Hobbit", "author": "Tolkien", "year": 1937, "isbn": "978-0"}'
```

List books by author:

```bash
curl "http://localhost:5000/books?author=Tolkien"
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1951}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Status codes

- `200` — success (GET, PUT)
- `201` — created (POST)
- `204` — deleted (DELETE)
- `400` — validation error (missing `title`/`author`, or invalid `year`)
- `404` — book not found

## Tests

```bash
python3 -m pytest
```
