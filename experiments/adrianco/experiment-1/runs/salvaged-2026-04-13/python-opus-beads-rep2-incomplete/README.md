# Books API

A simple REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

The API listens on `http://127.0.0.1:8000`. Interactive docs at `/docs`.

The SQLite database defaults to `books.db` in the working directory. Override with `BOOKS_DB=/path/to/file.db`.

## Endpoints

| Method | Path           | Description                         |
| ------ | -------------- | ----------------------------------- |
| GET    | `/health`      | Health check                        |
| POST   | `/books`       | Create a book                       |
| GET    | `/books`       | List books (optional `?author=`)    |
| GET    | `/books/{id}`  | Get a book by ID                    |
| PUT    | `/books/{id}`  | Update a book (partial supported)   |
| DELETE | `/books/{id}`  | Delete a book                       |

`POST` and `PUT` accept JSON with fields: `title` (required), `author` (required), `year`, `isbn`.

## Tests

```bash
pytest
```
