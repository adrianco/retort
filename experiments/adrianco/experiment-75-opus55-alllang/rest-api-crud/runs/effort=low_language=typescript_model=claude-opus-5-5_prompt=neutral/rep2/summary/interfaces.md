# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` health branch |
| POST | /books | `201 Book` / `400 {errors}` | `app.ts` `/books` POST branch |
| GET | /books | `200 [Book]` (`?author=` case-insensitive exact filter) | `app.ts` `/books` GET branch |
| GET | /books/{id} | `200 Book` / `404` | `app.ts` id-match GET branch |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `app.ts` id-match PUT branch |
| DELETE | /books/{id} | `204` / `404` | `app.ts` id-match DELETE branch |

Unmatched method on a known path returns `405`; malformed JSON body returns `400`; unexpected errors return `500`.

## Library API

- `createApp(dbPath = ":memory:") => http.Server` — builds the server with its own SQLite handle; closes the DB on server `close`.
- `validate(input) => { book?, errors[] }` — field validation for create/update.
- `Book` interface: `{ id, title, author, year|null, isbn|null }`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT). Backed by Node's built-in `node:sqlite` (`DatabaseSync`); file-backed (`books.db`) in `server.ts`, in-memory in tests.
