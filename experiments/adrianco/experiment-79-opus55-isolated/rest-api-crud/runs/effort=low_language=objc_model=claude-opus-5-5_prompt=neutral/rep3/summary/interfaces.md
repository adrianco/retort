# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `BookAPI.m:handleMethod:` |
| POST | /books | 201 `Book` \| 400 | `BookAPI.m:saveBookWithID:body:` |
| GET | /books | 200 `[Book]` (`?author=` exact, case-insensitive filter) | `BookAPI.m:handleMethod:` |
| GET | /books/{id} | 200 `Book` \| 404 | `BookAPI.m:handleMethod:` |
| PUT | /books/{id} | 200 `Book` \| 400 \| 404 (full replacement) | `BookAPI.m:saveBookWithID:body:` |
| DELETE | /books/{id} | 204 \| 404 | `BookAPI.m:handleMethod:` |

Unsupported methods on a known path return 405; request bodies over 1 MB return 413.

## Library API

- `BookStore`: `createBookWithTitle:author:year:isbn:`, `booksWithAuthor:`, `bookWithID:`, `updateBookWithID:title:author:year:isbn:`, `deleteBookWithID:`
- `BookAPI`: `handleMethod:path:query:body:` → `APIResponse`
- `HTTPServer`: `startOnPort:error:`, `stop`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
