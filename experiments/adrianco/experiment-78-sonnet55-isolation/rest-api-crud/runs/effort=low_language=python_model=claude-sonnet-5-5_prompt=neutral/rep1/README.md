# Book Collection API

Flask + SQLite REST API.

## Setup
    python -m venv venv && . venv/bin/activate
    pip install -r requirements.txt

## Run
    python app.py            # http://localhost:5000 (env: PORT, BOOKS_DB)

## Endpoints
- `POST /books` `{title, author, year, isbn}` (title, author required) → 201
- `GET /books[?author=NAME]`
- `GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}` (204)
- `GET /health`

## Tests
    pytest
