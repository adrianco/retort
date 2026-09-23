# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `api.cpp:BookApi::handle` |
| POST | /books | 201 book \| 400 | `api.cpp:BookApi::create` |
| GET | /books (`?author=` exact filter) | 200 `[book]` | `api.cpp:BookApi::list` |
| GET | /books/{id} | 200 book \| 404 | `api.cpp:BookApi::get` |
| PUT | /books/{id} | 200 book \| 400 \| 404 | `api.cpp:BookApi::update` |
| DELETE | /books/{id} | 204 \| 404 | `api.cpp:BookApi::remove` |

Unmatched method on a known path returns 405; oversized body returns 413.

## Library API

`BookApi::handle(const Request&) -> Response` is the single dispatch entry point; `Request` carries `method`, `path`, `body`, and a parsed `query` map. `main.cpp` is a thin transport layer.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
