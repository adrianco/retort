# Book Collection API

A Flask REST API backed by SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The service listens on `http://127.0.0.1:5000`. It stores data in `books.db`; set `DATABASE_PATH` to use another SQLite file.

Endpoints:

- `GET /health`
- `POST /books` with JSON fields `title`, `author`, and optional `year`, `isbn`
- `GET /books?author=...`
- `GET`, `PUT`, and `DELETE /books/<id>`

`PUT` accepts the same JSON shape as creation and requires non-empty `title` and `author`.

## Test

```bash
pytest -q
```
