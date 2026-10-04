# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `app.ts:route` |
| POST | /books | `Book` (201) / 400 / 413 | `app.ts:route` → `store.create` |
| GET | /books | `[Book]` (200), optional `?author=` | `app.ts:route` → `store.list` |
| GET | /books/{id} | `Book` (200) / 400 / 404 | `app.ts:route` → `store.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 / 413 | `app.ts:route` → `store.update` |
| DELETE | /books/{id} | (204) / 400 / 404 | `app.ts:route` → `store.delete` |

Unknown paths → 404; unsupported methods → 405 with an `Allow` header.

## Library API

- `createApp(store: BookStore): Server` — builds the HTTP server.
- `BookStore(path)` — `create`, `list(author?)`, `get(id)`, `update(id, input)`, `delete(id)`, `close()`. Pass `":memory:"` for ephemeral.
- `validateBook(body): ValidationResult` — validates title/author (required), year (optional int), isbn (optional non-empty string).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
