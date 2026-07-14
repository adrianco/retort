# Interfaces

## HTTP routes (declared in `src/index.ts`)

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, timestamp}` 200 | `index.ts:36` |
| GET | /books | `[Book]` 200 (optional `?author=` LIKE filter) | `index.ts:41` |
| GET | /books/:id | `Book` 200 \| 404 | `index.ts:59` |
| POST | /books | `Book` 201 \| 400 (missing title/author) | `index.ts:75` |
| PUT | /books/:id | `Book` 200 \| 400 \| 404 | `index.ts:97` |
| DELETE | /books/:id | `{message}` 200 \| 404 | `index.ts:126` |

`src/server.ts` declares only `/health` inline and mounts `/books` from a non-existent `./routes/books` module.

## Data schema

`books` table (`index.ts:22`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT). Backed by a `./bookstore.db` SQLite file.

## Library API

(none) — `index.ts` exports nothing; `server.ts` exports `app` by default but does not compile.
