# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `book_api.cpp:BookApi::handle` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `book_api.cpp:BookApi::handle` |
| POST | /books | `Book` (201) / error (400/500) | `book_api.cpp:BookApi::handle` |
| GET | /books/{id} | `Book` (200) / 404 / 400 | `book_api.cpp:BookApi::handle` |
| PUT | /books/{id} | `Book` (200) / 404 / 400 | `book_api.cpp:BookApi::handle` |
| DELETE | /books/{id} | 204 / 404 / 400 | `book_api.cpp:BookApi::handle` |
| (any) | unmatched | 404 `{"error":...}` | `book_api.cpp:BookApi::handle` |

## Library API

`BookApi(database_path=":memory:")` — opens SQLite, creates schema. `HttpResponse handle(HttpRequest)` — pure dispatch, no sockets. `reason_phrase(int)` — status→phrase.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL DEFAULT '').
