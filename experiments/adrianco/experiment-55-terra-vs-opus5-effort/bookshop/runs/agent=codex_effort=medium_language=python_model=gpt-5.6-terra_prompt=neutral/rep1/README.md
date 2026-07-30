# Book Collection API

A Flask REST API backed by SQLite.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The server listens on `http://localhost:5000`. By default it stores data in
`books.db`; set `BOOKS_DATABASE` to use another SQLite file.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Service health check |
| POST | `/books` | Create a book |
| GET | `/books` | List books (`?author=Name` filters by exact author) |
| GET | `/books/{id}` | Get one book |
| PUT | `/books/{id}` | Replace a book |
| DELETE | `/books/{id}` | Delete a book |

Create and update requests accept JSON such as:

```json
{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

`title` and `author` are required non-empty strings. `year`, when supplied,
must be an integer; `isbn`, when supplied, must be a string.

## Tests

```bash
python3 -m pytest -q
```
