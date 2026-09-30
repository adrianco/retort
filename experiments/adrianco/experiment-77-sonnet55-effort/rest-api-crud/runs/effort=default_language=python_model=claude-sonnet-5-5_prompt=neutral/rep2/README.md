# Book Collection API

REST API for a book collection, written in Python using only the standard
library (`http.server`, `sqlite3`). No third-party runtime dependencies.

## Setup and run

```bash
python app.py              # listens on 127.0.0.1:8000, data in books.db
PORT=9000 DB_PATH=/tmp/b.db python app.py   # configurable via env
```

## Endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| POST | /books | Create (`title`, `author` required; `year` int, `isbn` string optional) | 201 |
| GET | /books | List; optional `?author=` exact-match filter | 200 |
| GET | /books/{id} | Get one | 200 |
| PUT | /books/{id} | Replace/update (same validation as POST) | 200 |
| DELETE | /books/{id} | Delete | 204 |
| GET | /health | Health check | 200 |

Errors return JSON `{"error": "..."}` with 400 (validation), 404, or 405.

```bash
curl -X POST localhost:8000/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"111"}'
```

## Tests

```bash
pip install pytest
python -m pytest -q
```
