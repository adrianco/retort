# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts:/health` |
| POST | /books | `201 Book` + `Location` / `400` | `app.ts:/books` |
| GET | /books | `200 [Book]` (`?author=` filter) / `400` | `app.ts:/books` |
| GET | /books/:id | `200 Book` / `404` | `app.ts:/books/:id` |
| PUT | /books/:id | `200 Book` / `400` / `404` | `app.ts:/books/:id` |
| DELETE | /books/:id | `204` / `404` | `app.ts:/books/:id` |
| * | (any other) | `404 {error:"not found"}` | catch-all handler |

## Library API

- `createApp(store: BookStore): Express`
- `BookStore` — `create`, `list(author?)`, `get(id)`, `update(id, input)`, `delete(id)`, `close()`
- `validateBook(body): ValidationResult` · `parseId(raw): number | undefined`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
