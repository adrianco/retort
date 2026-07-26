# Book Collection REST API

A small Flask + SQLite service for managing a book collection.

## Endpoints

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check                             |
| POST   | `/books`       | Create a book (`title`, `author` req'd)  |
| GET    | `/books`       | List books; optional `?author=` filter   |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`  | Delete a book                            |

Book payload fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional).

Responses are JSON. Status codes: `200 OK`, `201 Created`, `204 No Content`,
`400 Bad Request`, `404 Not Found`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py                       # listens on 0.0.0.0:5000
PORT=8080 python app.py             # override port
BOOKS_DB_PATH=/tmp/mine.db python app.py   # override SQLite location
```

Quick check:

```bash
curl -s localhost:5000/health
curl -s -X POST localhost:5000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -s 'localhost:5000/books?author=Frank%20Herbert'
```

## Tests

```bash
pytest -v
```

Each test uses a fresh temporary SQLite file, so runs are isolated.
