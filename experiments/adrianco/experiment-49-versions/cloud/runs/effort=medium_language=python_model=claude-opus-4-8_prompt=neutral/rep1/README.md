# Book Collection API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.8+
- Flask (see `requirements.txt`)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python3 app.py
```

The server starts on `http://localhost:5000`. Data is stored in a local
SQLite file `books.db` (created automatically on first request).

## Running the tests

```bash
python3 -m pytest
```

Tests run against an in-memory SQLite database, so they don't touch `books.db`.

## API

All request and response bodies are JSON.

### Health check

```
GET /health  ->  200 {"status": "ok"}
```

### Create a book

```
POST /books
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

- `title` and `author` are **required** (non-empty strings).
- `year` (optional) must be an integer; `isbn` (optional) must be a string.
- Returns `201` with the created book, or `400` on invalid input.

### List books

```
GET /books              ->  200 [ ...all books... ]
GET /books?author=Name  ->  200 [ ...books by that author... ]
```

### Get a single book

```
GET /books/{id}  ->  200 {book}  |  404 if not found
```

### Update a book

```
PUT /books/{id}
{ "title": "New title", "year": 2020 }
```

- Partial updates are supported; only the fields you send are changed.
- Provided `title`/`author` must still be non-empty.
- Returns `200` with the updated book, `404` if not found, or `400` on invalid input.

### Delete a book

```
DELETE /books/{id}  ->  204 No Content  |  404 if not found
```

## Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949}'

curl http://localhost:5000/books
```
