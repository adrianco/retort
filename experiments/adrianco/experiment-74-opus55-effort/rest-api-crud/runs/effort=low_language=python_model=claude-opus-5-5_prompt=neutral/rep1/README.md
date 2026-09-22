# Book Collection API

Flask + SQLite REST service for managing books.

## Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python app.py            # http://localhost:5000 (PORT and BOOKS_DB env vars optional)
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status": "ok"}` |
| POST | /books | JSON `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` (case-insensitive exact match) |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace, same validation as POST |
| DELETE | /books/{id} | 204 |

## Test
```bash
pytest -q
```
