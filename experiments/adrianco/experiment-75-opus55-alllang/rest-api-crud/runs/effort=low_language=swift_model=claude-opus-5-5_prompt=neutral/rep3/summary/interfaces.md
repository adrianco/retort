# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `Router.swift:handle` (health case) |
| GET | /books | `200 [Book]` (optional `?author=` filter, case-insensitive) | `Router.swift:handle` → `BookStore.list` |
| POST | /books | `201 Book` \| `400` bad JSON \| `422` validation | `Router.swift:handle` → `validate` → `BookStore.create` |
| GET | /books/{id} | `200 Book` \| `400` bad id \| `404` | `Router.swift:handle` → `BookStore.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` \| `422` | `Router.swift:handle` → `validate` → `BookStore.update` |
| DELETE | /books/{id} | `204` \| `404` | `Router.swift:handle` → `BookStore.delete` |

Unmatched method on a known path returns `405`; unknown path returns `404`.

## Library API

- `BookStore(path:)` — `create`, `list(author:)`, `get`, `update`, `delete`; NSLock-guarded SQLite access.
- `Router(store:)` — `handle(HTTPRequest) -> HTTPResponse`, transport-independent.
- `HTTPServer(port:router:)` — `start()`, static `parse(_:)`.

## Data schema

`books` table: `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
