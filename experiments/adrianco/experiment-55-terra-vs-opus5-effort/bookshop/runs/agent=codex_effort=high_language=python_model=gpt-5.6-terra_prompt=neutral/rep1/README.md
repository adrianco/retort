# Book Collection API

A Flask REST API backed by SQLite.

## Setup and run

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server listens on `http://127.0.0.1:5000` by default and stores its data in
`books.db` in this directory. Set `PORT` to use a different port.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List books; optional exact `?author=` filter |
| `GET` | `/books/{id}` | Retrieve a book |
| `PUT` | `/books/{id}` | Update one or more book fields |
| `DELETE` | `/books/{id}` | Delete a book |

Book request bodies are JSON. `title` and `author` must be non-empty strings
when creating a book. `year` is an optional integer and `isbn` is an optional
string. Updates preserve unspecified fields.

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}'
```

Successful creates return `201`, reads and updates return `200`, and deletion
returns `204`. Invalid input returns JSON with `400`; missing books return JSON
with `404`.

## Tests

```bash
python -m unittest -v
```
