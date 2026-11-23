# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` | `Books.m:route` (line 50) |
| POST | /books | `Book` (201) | `Books.m:route` (lines 84–86) |
| GET | /books | `[Book]` (200) | `Books.m:route` (line 65) |
| GET | /books?author= | `[Book]` filtered, exact case-sensitive match | `Books.m:route` (lines 62–64) |
| GET | /books/{id} | `Book` \| 404 | `Books.m:route` (line 67) |
| PUT | /books/{id} | `Book` \| 404 | `Books.m:route` (line 88) |
| DELETE | /books/{id} | `{"id":N}` \| 404 | `Books.m:route` (lines 68–69) |

Unsupported method on a known path → 405. Unknown path → 404. Oversized body → 413.
`transfer-encoding` header rejected → 400 (Content-Length only).

## Data schema

`books` table (`Books.m:138-139`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Runtime surface

CLI: `./books` runs a loopback TCP server (`PORT`, default 8080); `./books --stdio`
serves a single HTTP request over stdin/stdout. DB path from `BOOKS_DB` (default
`books.sqlite3`).
