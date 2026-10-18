# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `book_api.cpp:handle` (L103) |
| POST | /books | `201 Book \| 400` | `book_api.cpp:handle` (L105) |
| GET | /books | `200 [Book]` (optional `?author=`) | `book_api.cpp:handle` (L118) |
| GET | /books/{id} | `200 Book \| 404` | `book_api.cpp:handle` (L125) |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `book_api.cpp:handle` (L127) |
| DELETE | /books/{id} | `204 \| 404` | `book_api.cpp:handle` (L126) |

Other paths/methods return `404` or `405` with a JSON `{"error":...}` body.

## Library API

- `BookApi(const std::string& database_path)` — opens/creates the SQLite DB and `books` table.
- `HttpResponse BookApi::handle(method, target, body)` — pure request→response entry point (no sockets), which is what the tests drive directly.
- `std::string reason_phrase(int status)` — maps status code to HTTP reason phrase.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
