# Books REST API

A simple Flask + SQLite REST service for managing a book collection.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service listens on `http://0.0.0.0:5000`. The SQLite database file
defaults to `books.db` in the project directory; override with the
`BOOKS_DB` environment variable.

## Endpoints

| Method | Path           | Description                                    |
|--------|----------------|------------------------------------------------|
| GET    | /health        | Health check                                   |
| POST   | /books         | Create a book (`title`, `author` required)     |
| GET    | /books         | List books; filter with `?author=NAME`         |
| GET    | /books/{id}    | Get one book                                   |
| PUT    | /books/{id}    | Update a book                                  |
| DELETE | /books/{id}    | Delete a book                                  |

### Book fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

### Example

```bash
curl -X POST http://localhost:5000/books \
    -H 'Content-Type: application/json' \
    -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

## Tests

```bash
pytest
```
