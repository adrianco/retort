# Books REST API

A simple FastAPI + SQLite REST API for managing a book collection.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

The service listens on `http://localhost:8000`.

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book (JSON: `title`, `author`, optional `year`, `isbn`)
- `GET /books` — list books; filter with `?author=Name`
- `GET /books/{id}` — get a single book
- `PUT /books/{id}` — update a book
- `DELETE /books/{id}` — delete a book

`title` and `author` are required.

## Tests

```bash
pytest -v
```
