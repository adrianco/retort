# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.cpp:route` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive filter) | `app.cpp:route` → `BookStore::list` |
| POST | /books | `201 Book` / `400 {error}` | `app.cpp:route` → `parse_book` → `BookStore::create` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `app.cpp:route` → `BookStore::get` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `app.cpp:route` → `parse_book` → `BookStore::update` |
| DELETE | /books/{id} | `204` / `404 {error}` | `app.cpp:route` → `BookStore::remove` |

Unmatched method on a known path returns `405`; unknown path returns `404`. Malformed/oversized requests return `400`/`413` at the socket layer.

## Library API

- `handle_request(BookStore&, const Request&) -> Response` — transport-independent router (never throws; internal errors → 500).
- `BookStore` — `create`, `list(author?)`, `get(id)`, `update(id, book)`, `remove(id)`.
- `json::parse(string) -> optional<Value>`, `json::quote(string)`.
- `HttpServer(Handler)` — `listen(host, port) -> port`, `run()`, `stop()`.

## Data schema

`books` table: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `title TEXT NOT NULL`, `author TEXT NOT NULL`, `year INTEGER` (nullable), `isbn TEXT` (nullable). Index `idx_books_author` on `author COLLATE NOCASE`.
