# Interfaces

## HTTP routes

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| GET | /health | Liveness, returns `{"status":"ok"}` | works |
| POST | /books | Create book (title, author required; year, isbn optional) → 201 | works |
| GET | /books | List books, optional `?author=` exact-match filter | works |
| GET | /books/{id} | Get one book by id → 200 / 404 | **broken** — route literal under axum 0.7, never matches numeric id |
| PUT | /books/{id} | Replace a book → 200 / 404 | **broken** — same |
| DELETE | /books/{id} | Delete a book → 204 / 404 | **broken** — same |

## Data schema

`books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)`

## Error contract

`ApiError` → JSON `{"error": <msg>}` with 400 (validation), 404 (not found),
500 (database). Validation rejects empty/whitespace `title` or `author`.
