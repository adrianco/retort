# Book Collection API

Flask + SQLite REST API for managing books.

## Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python app.py            # serves on http://localhost:5000 (PORT env to change)
```
The database file defaults to `books.db`; override with `BOOKS_DB=/path/to.db`.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | Optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | Full replace, same validation as POST |
| DELETE | /books/{id} | 204 on success |

## Test
```bash
pytest -q
```
