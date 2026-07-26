# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
Python standard-library **`sqlite3`** module. Data is persisted to a local
SQLite database file (`books.db` by default).

## Requirements

- Python 3.8+
- Flask (see `requirements.txt`)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the service

```bash
python app.py
```

The server listens on `http://localhost:5000`. A `books.db` SQLite file is
created automatically on first run.

## Running the tests

```bash
pytest
```

Each test runs against its own throwaway SQLite database file, so the tests are
fully isolated and leave no state behind.

## API

All request and response bodies are JSON.

### Health check

```
GET /health  ->  200 {"status": "ok"}
```

### Create a book

```
POST /books
{
  "title":  "The Go Programming Language",   // required
  "author": "Alan Donovan",                   // required
  "year":   2015,                             // optional integer
  "isbn":   "978-0134190440"                  // optional string
}
->  201 Created  (returns the created book with its id)
->  400 Bad Request  (validation errors, e.g. missing title/author)
```

### List books

```
GET /books                ->  200  [ ...all books... ]
GET /books?author=Donovan ->  200  [ ...books by that author... ]
```

### Get one book

```
GET /books/{id}  ->  200 book
                 ->  404 {"error": "book not found"}
```

### Update a book

Partial updates are supported — send only the fields you want to change.

```
PUT /books/{id}
{ "title": "New Title" }
->  200 updated book
->  400 Bad Request  (validation errors)
->  404 Not Found
```

### Delete a book

```
DELETE /books/{id}  ->  204 No Content
                    ->  404 {"error": "book not found"}
```

## Example with curl

```bash
curl -s -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965}'

curl -s localhost:5000/books
curl -s 'localhost:5000/books?author=Herbert'
```

## Project layout

| File            | Purpose                                        |
| --------------- | ---------------------------------------------- |
| `app.py`        | Flask application and route handlers            |
| `db.py`         | SQLite connection helper and schema setup       |
| `test_app.py`   | Integration tests (pytest)                      |
| `requirements.txt` | Python dependencies                          |
