# Book Collection API

A small Flask REST API that stores books in SQLite.

## Setup and run

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API listens on `http://127.0.0.1:5000`. By default its SQLite database is
created at `instance/books.sqlite`. Set `BOOKS_DATABASE` to use another path.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok"}`. |
| `POST` | `/books` | Creates a book; `title` and `author` are required. |
| `GET` | `/books` | Lists books; use `?author=Name` to filter exactly by author. |
| `GET` | `/books/{id}` | Fetches one book. |
| `PUT` | `/books/{id}` | Replaces a book; `title` and `author` are required. |
| `DELETE` | `/books/{id}` | Deletes a book. |

The optional fields are `year` (integer) and `isbn` (string). Successful
creation returns `201`, retrieval/update returns `200`, and deletion returns
`204`. Invalid input returns `400`; a missing book returns `404`.

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969}'
```

## Tests

```bash
pytest -q
```
