# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` 200 | `app.ts:10` |
| POST | /books | `Book` 201 / errors 400 | `app.ts:14` |
| GET | /books | `[Book]` 200 (optional `?author=`) | `app.ts:30` |
| GET | /books/:id | `Book` 200 / 404 / 400 | `app.ts:43` |
| PUT | /books/:id | `Book` 200 / 404 / 400 | `app.ts:59` |
| DELETE | /books/:id | 204 / 404 / 400 | `app.ts:83` |

Malformed JSON bodies are caught by an error middleware returning 400 (`app.ts:98`).

## Library API

- `createApp(db: DatabaseSync): Express` — app factory (dependency-injected DB, enables in-memory test DBs)
- `createDb(path=":memory:"): DatabaseSync` — opens SQLite and creates the `books` table
- `validateBookInput(body): ValidationResult` — required title/author, optional integer year, optional string isbn

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
