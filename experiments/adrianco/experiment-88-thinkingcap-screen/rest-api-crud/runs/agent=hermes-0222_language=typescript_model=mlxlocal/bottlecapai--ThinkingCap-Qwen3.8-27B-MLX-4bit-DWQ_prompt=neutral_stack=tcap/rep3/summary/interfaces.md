# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, uptime}` | `app.ts` health handler |
| GET | / | `200 {name, status, endpoints[]}` | `app.ts` root handler (service info; added for readiness probe) |
| POST | /books | `201 Book` \| `400 {error}` | `app.ts` create handler → `db.createBook` |
| GET | /books | `200 [Book]` (optional `?author=`, case-insensitive) | `app.ts` list handler → `db.listBooks` |
| GET | /books/:id | `200 Book` \| `400` \| `404 {error}` | `app.ts` get handler → `db.getBook` |
| PUT | /books/:id | `200 Book` \| `400` \| `404 {error}` | `app.ts` update handler → `db.updateBook` |
| DELETE | /books/:id | `204` \| `400` \| `404 {error}` | `app.ts` delete handler → `db.deleteBook` |
| * | (unmatched) | `404 {error:"Not found"}` | fallthrough handler |

A central error-handling middleware maps malformed JSON bodies to `400 {error:"Invalid JSON body"}` and unexpected errors to `500`.

## Data schema

`books` table (SQLite via `node:sqlite`):
`id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable). Index `idx_books_author` on `author`.

## Library API

`createApp(database: DatabaseSync): Express` — app factory taking an injected DB handle (tests pass `:memory:`).
`validateBookPayload(body, {partial?}): {patch, errors}` — validates/sanitizes create (full) and update (partial) payloads.
