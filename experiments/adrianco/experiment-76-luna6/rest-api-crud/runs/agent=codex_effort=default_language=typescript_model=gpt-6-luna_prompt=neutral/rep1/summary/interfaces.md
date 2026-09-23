# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `server.ts` inline |
| GET | /books | `[Book]` (200), optional `?author=` filter | `server.ts` inline |
| POST | /books | `Book` (201) / `{error}` (400) | `server.ts` inline |
| GET | /books/{id} | `Book` (200) / `{error}` (404) | `server.ts` inline |
| PUT | /books/{id} | `Book` (200) / `{error}` (400/404) | `server.ts` inline |
| DELETE | /books/{id} | `{message}` (200) / `{error}` (404) | `server.ts` inline |

## Library API

- `createApp(options?: { databasePath?; database? }) => { server, close }` — exported factory.
- `Book` interface: `{ id, title, author, year, isbn }`.

## Data schema

`books` table: `id` (TEXT, pk = UUID), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NOT NULL). Index `books_author_idx` on `author`.
