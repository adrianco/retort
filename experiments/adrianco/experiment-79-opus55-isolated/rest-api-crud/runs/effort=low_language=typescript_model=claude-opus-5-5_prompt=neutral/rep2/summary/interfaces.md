# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:20` |
| POST | /books | `201 Book` / `400` | `app.ts:24` |
| GET | /books | `200 [Book]` (`?author=` exact, case-insensitive) / `400` | `app.ts:34` |
| GET | /books/:id | `200 Book` / `400` / `404` | `app.ts:43` |
| PUT | /books/:id | `200 Book` (full replace) / `400` / `404` | `app.ts:54` |
| DELETE | /books/:id | `204` / `400` / `404` | `app.ts:70` |
| * | (unmatched) | `404 {error:"not found"}` | `app.ts:80` |

## Library API

- `createApp(store: BookStore): Express` — wires routes onto an Express app.
- `BookStore(filename)` with `create/list/get/update/delete/close`.
- `validateBook(body): ValidationResult` — tagged-union result.

## Data schema

`books` table: `id INTEGER PK AUTOINCREMENT`, `title TEXT NOT NULL`, `author TEXT NOT NULL`, `year INTEGER`, `isbn TEXT`.
