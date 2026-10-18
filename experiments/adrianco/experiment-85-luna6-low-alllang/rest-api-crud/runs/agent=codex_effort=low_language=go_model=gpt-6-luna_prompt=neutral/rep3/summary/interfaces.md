# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `main.go:ServeHTTP` |
| POST | /books | `201 Book \| 400` | `main.go:API.create` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `main.go:API.list` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `main.go:API.book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `main.go:API.book` |
| DELETE | /books/{id} | `204 \| 404` | `main.go:API.book` |

## Data schema

`books` table (SQLite, `modernc.org/sqlite` pure-Go driver):
id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER default 0), isbn (TEXT default '').

## Library API

Exported: `Book`, `API`, `NewAPI(db)`, `OpenDB(path)`.
