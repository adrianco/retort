# Book Collection API

Flask + SQLite REST API for managing books.

## Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python app.py            # serves on http://localhost:5000 (PORT env overrides)
```
Database file defaults to `books.db`; override with `BOOKS_DB=/path/to.db`.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replacement, same validation as POST |
| DELETE | /books/{id} | 204 on success |

## Tests
```bash
pytest -q
```
