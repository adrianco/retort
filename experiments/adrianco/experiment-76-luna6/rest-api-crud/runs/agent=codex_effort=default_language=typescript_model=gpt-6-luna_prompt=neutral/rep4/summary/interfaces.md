# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` inline |
| GET | /books | `200 [Book]` (optional `?author=` case-insensitive exact filter) | `app.ts` inline |
| POST | /books | `201 Book` \| `400` | `app.ts` inline |
| GET | /books/{id} | `200 Book` \| `404` \| `400` (bad id) | `app.ts` inline |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `app.ts` inline |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `app.ts` inline |

Unknown routes return `404 {error:"Route not found"}`; unhandled exceptions return `500`.

## Exported library API

- `createApp(db?)` — builds an `http.Server`; DB path from `DATABASE_PATH` (default `books.sqlite`).
- `createHandler(db)` — creates the table and returns the request handler (used directly by tests).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Access via `node:sqlite` `DatabaseSync` with prepared statements.
