# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `app.ts` /health |
| POST | /books | `Book` (201) / `{errors}` (400) | `app.ts` POST /books |
| GET | /books?author= | `[Book]` (200) | `app.ts` GET /books |
| GET | /books/:id | `Book` (200) / 404 / 400 invalid id | `app.ts` GET /books/:id |
| PUT | /books/:id | `Book` (200) / 400 / 404 | `app.ts` PUT /books/:id |
| DELETE | /books/:id | 204 / 404 / 400 invalid id | `app.ts` DELETE /books/:id |
| * | (fallback) | `{error:"not found"}` (404) | `app.ts` catch-all |

Malformed JSON bodies are caught by an Express error middleware → 400 `{error:"malformed JSON"}`.

## Library API

- `createApp(repo: BookRepository)` → Express app.
- `BookRepository(path=":memory:")` with `list(author?)`, `get(id)`, `create(b)`, `update(id, b)`, `delete(id)`, `close()`.
- `validateBook(body)` → `{ok:true, value}` | `{ok:false, errors[]}`.

## Data schema

`books` table (SQLite via `node:sqlite`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
