# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` health handler |
| POST | /books | `201 Book` \| `400` | `app.ts` create handler → `store.create` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.ts` list handler → `store.list` |
| GET | /books/:id | `200 Book` \| `404` | `app.ts` get handler → `store.get` |
| PUT | /books/:id | `200 Book` \| `400` \| `404` | `app.ts` update handler → `store.update` |
| DELETE | /books/:id | `204` \| `404` | `app.ts` delete handler → `store.delete` |

Unmatched routes return `404 {error:"not found"}`; malformed JSON bodies are caught by an error middleware and return `400`.

## Library API

- `createApp(store: BookStore): express.Application` — builds the configured app.
- `validateBook(body: unknown): {value} | {errors}` — pure validation.
- `BookStore(path=":memory:")` with `create`, `list`, `get`, `update`, `delete`, `close`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
