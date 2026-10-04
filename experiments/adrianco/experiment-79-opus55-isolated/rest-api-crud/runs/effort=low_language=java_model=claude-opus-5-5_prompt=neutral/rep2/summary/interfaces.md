# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `BookServer.java:90` (pings DB) |
| POST | /books | `201 Book` + Location header / `400` | `BookServer.java:97` |
| GET | /books | `200 [Book]`; `?author=` filters (case-insensitive) | `BookServer.java:96` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `BookServer.java:107` |
| PUT | /books/{id} | `200 Book` (full replace) / `400` / `404` | `BookServer.java:108` |
| DELETE | /books/{id} | `204` / `400` / `404` | `BookServer.java:109` |

Unmatched paths → `404`; wrong method on a known path → `405` with `Allow` header.

## Data schema

`books` table (SQLite): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

`BookRepository`: `create`, `list(author)`, `find(id)`, `update(id, book)`,
`delete(id)`, `ping`, `close` (AutoCloseable). `BookServer(repo, port)` with
`start`/`stop`/`port`.
