# Book Collection API

Flask + SQLite REST API.

## Setup
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt

## Run
    python app.py        # http://localhost:5000 (env: PORT, BOOKS_DB)

## Endpoints
- `POST /books` — body `{title, author, year, isbn}` (title, author required) → 201
- `GET /books[?author=NAME]`
- `GET /books/{id}`
- `PUT /books/{id}` — full update
- `DELETE /books/{id}` → 204
- `GET /health`

Errors return JSON `{"error": "..."}` with 400 / 404.

## Test
    pytest
