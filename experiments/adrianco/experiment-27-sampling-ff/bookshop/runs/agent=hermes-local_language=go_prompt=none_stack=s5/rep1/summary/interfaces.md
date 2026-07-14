# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `handlers.go:HealthCheck` |
| POST | /books | `201 Book \| 400 \| 409` | `handlers.go:CreateBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.go:ListBooks` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:GetBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:UpdateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `handlers.go:DeleteBook` |

## CLI commands

(none) — server configured via `PORT` and `DB_PATH` env vars.

## Library API

Exported store: `BookStore` with `Create`, `GetAll(authorFilter)`, `GetByID`, `Update`, `Delete`, `Close`.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`): id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER NOT NULL), isbn (TEXT NOT NULL UNIQUE), created_at (TEXT), updated_at (TEXT nullable).
