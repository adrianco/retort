# Book Collection API

Flask + SQLite REST API.

## Setup
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt

## Run
    python app.py            # http://127.0.0.1:5000 (env: PORT, BOOKS_DB)

## Endpoints
- `GET /health`
- `POST /books` — JSON `{title, author, year, isbn}`; title and author required (400 otherwise)
- `GET /books[?author=Name]`
- `GET /books/{id}` — 404 if missing
- `PUT /books/{id}` — full update, same validation
- `DELETE /books/{id}` — 204

## Tests
    pytest
