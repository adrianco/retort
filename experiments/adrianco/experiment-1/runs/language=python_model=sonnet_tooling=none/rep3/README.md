# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

`title` and `author` are required. `year` and `isbn` are optional.

### List books

```bash
curl http://localhost:5000/books
curl "http://localhost:5000/books?author=Orwell"
```

## Tests

```bash
pytest test_app.py -v
```
