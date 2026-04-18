# Books REST API

A minimal Flask + SQLite REST API for managing a book collection.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on port 5000 by default (override with `PORT`).
Data is stored in `books.db` (override with `BOOKS_DB`).

## Endpoints

| Method | Path          | Description                            |
| ------ | ------------- | -------------------------------------- |
| GET    | `/health`     | Health check — returns `{"status":"ok"}` |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List books; supports `?author=` filter |
| GET    | `/books/{id}` | Get a book                             |
| PUT    | `/books/{id}` | Update a book (partial updates allowed) |
| DELETE | `/books/{id}` | Delete a book                          |

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441013593"}'
```

## Tests

```bash
pytest -v
```
