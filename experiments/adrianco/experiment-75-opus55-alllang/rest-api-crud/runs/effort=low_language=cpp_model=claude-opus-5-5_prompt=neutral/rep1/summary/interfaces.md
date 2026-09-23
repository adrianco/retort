# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `book_api.cpp:handle` |
| POST | /books | `201 Book` / `400 {error}` | `book_api.cpp:create` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `book_api.cpp:list` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `book_api.cpp:get` |
| PUT | /books/{id} | `200 Book` / `400` / `404 {error}` | `book_api.cpp:update` |
| DELETE | /books/{id} | `204` / `404 {error}` | `book_api.cpp:remove` |

Unmatched methods on a known path return `405`; unknown paths return `404`. Request bodies over 1 MiB return `413`.

## Library API

`BookApi::handle(method, target, body) -> Response{status, body}` — the single entry point, independent of the socket layer (which is what makes it directly testable). Helpers `parse_json_object`, `json_escape`, `url_decode` are exported from the header.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).
