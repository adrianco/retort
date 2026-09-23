# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `Router.swift:handle` |
| POST | /books | 201 `Book` / 400 validation / 400 invalid JSON | `Router.swift:handle` → `store.create` |
| GET | /books[?author=] | 200 `[Book]` (optionally author-filtered) | `Router.swift:handle` → `store.list` |
| GET | /books/{id} | 200 `Book` / 400 invalid id / 404 | `Router.swift:handle` → `store.get` |
| PUT | /books/{id} | 200 `Book` / 400 validation / 404 | `Router.swift:handle` → `store.update` |
| DELETE | /books/{id} | 204 / 404 | `Router.swift:handle` → `store.delete` |

## Library API

- `BookStore(path:)` — `list(author:)`, `get(_:)`, `create(_:)`, `update(_:_:)`, `delete(_:)`
- `Router(store:)` — `handle(method:target:body:)`
- `HTTPServer(port:router:)` — `start()`, `stop()`, `port`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
