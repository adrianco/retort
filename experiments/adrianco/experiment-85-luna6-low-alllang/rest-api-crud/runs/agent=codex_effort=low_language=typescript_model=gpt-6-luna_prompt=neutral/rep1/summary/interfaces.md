# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` health handler |
| POST | /books | `201 Book \| 400` | `app.ts` create handler |
| GET | /books | `200 [Book]` (optional `?author=` filter, case-insensitive) | `app.ts` list handler |
| GET | /books/:id | `200 Book \| 400 \| 404` | `app.ts` get-by-id handler |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `app.ts` update handler |
| DELETE | /books/:id | `204 \| 400 \| 404` | `app.ts` delete handler |

## Library API

- `createApp(database?: DatabaseSync)` — returns a configured Express app; accepts an injected `node:sqlite` database (defaults to `books.sqlite` on disk), enabling in-memory DBs for tests.
- `Book` interface — `{ id, title, author, year, isbn }`.

## Data schema

`books` table (SQLite via `node:sqlite` `DatabaseSync`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT.
