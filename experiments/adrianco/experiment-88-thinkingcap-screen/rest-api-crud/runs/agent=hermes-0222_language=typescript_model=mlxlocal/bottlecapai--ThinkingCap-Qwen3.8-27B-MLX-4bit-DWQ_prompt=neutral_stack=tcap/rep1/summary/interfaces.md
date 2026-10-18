# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` /health handler |
| POST | /books | `201 Book \| 400` | `app.ts` POST /books |
| GET | /books | `200 [Book]` (optional `?author=` exact-match filter) | `app.ts` GET /books |
| GET | /books/:id | `200 Book \| 400 \| 404` | `app.ts` GET /books/:id |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `app.ts` PUT /books/:id |
| DELETE | /books/:id | `204 \| 400 \| 404` | `app.ts` DELETE /books/:id |
| (any) | /* unmatched | `404 {error:"Not found"}` | fallthrough middleware |

## Library API

- `createApp(dbPath = "books.db"): Express` — builds the configured app; `":memory:"` for tests.
- `createDb(dbPath): Database` — opens/initializes the SQLite DB.
- `ValidationError extends Error` — carries HTTP 400 semantics.
- `Book` interface — `{ id, title, author, year|null, isbn|null }`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). WAL journal mode.
