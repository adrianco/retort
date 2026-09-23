# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `Router.swift:41` |
| GET | /books | 200 `[Book]` (optional `?author=` case-insensitive exact filter) | `Router.swift:45` |
| POST | /books | 201 `Book`; 400 on invalid JSON / missing title or author | `Router.swift:48` |
| GET | /books/{id} | 200 `Book`; 400 invalid id; 404 missing | `Router.swift:58` |
| PUT | /books/{id} | 200 `Book`; 400 invalid; 404 missing | `Router.swift:61` |
| DELETE | /books/{id} | 204; 404 missing | `Router.swift:68` |
| (other) | /books, /books/{id} | 405 method not allowed | `Router.swift:53,71` |

## Library API

- `BookStore(path:)` — opens SQLite (`:memory:` supported), `create/list/get/update/delete`.
- `Router(store:)` — `handle(HTTPRequest) -> HTTPResponse`.
- `HTTPServer(port:router:)` — `start(ready:)`, `stop()`, static `parse(Data) -> HTTPRequest?`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER nullable), `isbn` (TEXT nullable).
