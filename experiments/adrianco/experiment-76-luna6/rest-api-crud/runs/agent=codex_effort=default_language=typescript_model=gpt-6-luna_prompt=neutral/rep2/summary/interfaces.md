# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `books.ts:64` |
| GET | /books | `200 [Book]` (optional `?author=` filter, case-insensitive) | `books.ts:65` |
| POST | /books | `201 Book` \| `400 {error}` | `books.ts:72` |
| GET | /books/{id} | `200 Book` \| `404` | `books.ts:88` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `books.ts:92` |
| DELETE | /books/{id} | `200 {message}` \| `404` | `books.ts:104` |

Any other path/method → `404 {error:"Not found"}`.

## Library API

- `createBookServer(databasePath?)` → `{ server, close }` — factory that opens the DB, creates the table, and returns an unbound `http.Server` plus a `close()` that shuts the DB.
- `Book` interface: `{ id, title, author, year: number|null, isbn: string|null }`.

## Data schema

`books` table (SQLite via `node:sqlite`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT.
