# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `server.ts` inline |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `server.ts` → `BookStore.list` |
| POST | /books | `Book` (201) / `{error}` (400) | `server.ts` → `BookStore.create` |
| GET | /books/:id | `Book` (200) / `{error}` (404) / `{error}` (400 non-int id) | `server.ts` → `BookStore.get` |
| PUT | /books/:id | `Book` (200) / `{error}` (404) / `{error}` (400) | `server.ts` → `BookStore.update` |
| DELETE | /books/:id | `{message}` (200) / `{error}` (404) | `server.ts` → `BookStore.delete` |
| (any) | (unmatched) | `{error:"Not found"}` (404) | `server.ts` inline |

## Library API

- `BookStore(filename?)` — `list(author?)`, `get(id)`, `create(input)`, `update(id, input)`, `delete(id)`, `close()`
- `createApp(store?)` — returns `{ server, store }`; the `http.Server` is not yet listening.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
