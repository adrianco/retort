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

The service listens on `http://localhost:5000` and stores data in `books.db`
(override with the `BOOKS_DB` env var).

## Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check                             |
| POST   | `/books`        | Create a book (`title`, `author` req'd)  |
| GET    | `/books`        | List books; `?author=` filter supported  |
| GET    | `/books/{id}`   | Get a book by id                         |
| PUT    | `/books/{id}`   | Update a book (partial fields allowed)   |
| DELETE | `/books/{id}`   | Delete a book                            |

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:5000/books?author=Frank%20Herbert
```

## Tests

```bash
pytest -v
```
