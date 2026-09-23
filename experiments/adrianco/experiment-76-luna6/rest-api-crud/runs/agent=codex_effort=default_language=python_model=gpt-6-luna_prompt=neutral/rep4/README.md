# Books API

A JSON REST API for managing books, built with Flask and SQLite.

## Setup

Use Python 3.9 or newer. Create and activate a virtual environment, then install dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
python app.py
```

The service listens at `http://127.0.0.1:5000`. SQLite creates `books.db` in the project directory. Set `BOOKS_DATABASE` to use another database file.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book; JSON requires `title` and `author`, with optional `year` and `isbn`
- `GET /books` — list books; optionally filter with `?author=Name`
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book; requires `title` and `author`, optional `year` and `isbn`
- `DELETE /books/{id}` — delete a book

Successful creation returns `201`, deletion returns `204`, missing books return `404`, and invalid input returns `400`.

## Tests

```sh
python -m unittest discover -s tests -v
```
