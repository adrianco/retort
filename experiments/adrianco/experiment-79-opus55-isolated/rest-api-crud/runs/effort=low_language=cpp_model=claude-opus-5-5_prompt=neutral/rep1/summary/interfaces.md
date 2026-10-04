# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.cpp:route` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.cpp:route` → `BookStore::list` |
| POST | /books | `201 Book` / `400` on invalid body | `app.cpp:route` → `parse_book` → `BookStore::create` |
| GET | /books/{id} | `200 Book` / `404` | `app.cpp:route` → `BookStore::get` |
| PUT | /books/{id} | `200 Book` / `400` / `404` (full replace) | `app.cpp:route` → `BookStore::update` |
| DELETE | /books/{id} | `204` / `404` | `app.cpp:route` → `BookStore::remove` |

Unmatched methods on a known path return `405`; unknown paths return `404`. All error bodies are JSON `{"error": "..."}`. Malformed HTTP → `400`, oversized body → `413`, internal exceptions → `500`.

## Library API

- `App(BookStore&)` — `Response handle(const Request&)` (never throws).
- `BookStore(path)` — `create`, `list(optional<author>)`, `get(id)`, `update(id,data)`, `remove(id)`.
- `Server(App&)` — `start(host,port)` (port 0 = ephemeral), `port()`, `stop()`.
- `json::parse(text) -> optional<Value>`, `json::quote(s)`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable). Index `idx_books_author` on `author`.
