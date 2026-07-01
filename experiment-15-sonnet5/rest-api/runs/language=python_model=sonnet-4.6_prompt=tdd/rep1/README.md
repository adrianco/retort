# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
pip install fastapi sqlalchemy httpx pytest
```

## Run

```bash
uvicorn app:app --reload
```

The API listens on `http://localhost:8000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Book fields

| Field | Type | Required |
|-------|------|----------|
| title | string | yes |
| author | string | yes |
| year | integer | no |
| isbn | string | no |

## Tests

```bash
python -m pytest test_app.py -v
```
