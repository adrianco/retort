# Interfaces

## HTTP routes

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| GET | `/health` | Liveness check `{"status":"ok"}` | 200 | 405 |
| POST | `/books` | Create a book | 201 (+`Location`) | 400, 413, 405 |
| GET | `/books` | List books, optional `?author=` (case-insensitive, exact) | 200 | 405 |
| GET | `/books/{id}` | Fetch one book | 200 | 404 |
| PUT | `/books/{id}` | Full-replace a book | 200 | 400, 404, 413 |
| DELETE | `/books/{id}` | Delete a book (empty body) | 204 | 404 |
| * | unknown path | | | 404 |

## Data schema (SQLite `books`)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| title | TEXT NOT NULL | required, trimmed |
| author | TEXT NOT NULL | required, trimmed |
| year | INTEGER | optional, `bool` rejected |
| isbn | TEXT | optional |

## Library API

- `create_server(host, port, db_path, quiet)` → `ThreadingHTTPServer` (port=0 for ephemeral).
- `BookStore(path)` — `create/list/get/update/delete`, connection-per-op (thread-safe).
- `validate_book(data)` → cleaned dict or `ApiError(400)`.
