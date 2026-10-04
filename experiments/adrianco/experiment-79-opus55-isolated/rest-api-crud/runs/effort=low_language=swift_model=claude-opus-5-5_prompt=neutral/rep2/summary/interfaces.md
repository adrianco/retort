# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` \| `503` | `App.swift:route` (health case) |
| GET | /books | `200 [Book]` (`?author=` filters, case-insensitive) | `App.swift:route` → `BookStore.list` |
| POST | /books | `201 Book` (+ `Location` header) \| `400` | `App.swift:route` → `BookStore.create` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `App.swift:route` → `BookStore.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `App.swift:route` → `BookStore.update` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `App.swift:route` → `BookStore.delete` |

Unknown paths → 404; unsupported methods → 405 with an `Allow` header.

## Library API (BookAPI module)

- `BookStore(path:)` — `create`, `list(author:)`, `get(id:)`, `update(id:_:)`, `delete(id:)`, `ping()`
- `BookApp(store:)` — `handle(_ request: HTTPRequest) -> HTTPResponse`
- `HTTPServer(app:)` — `start(host:port:)`, `stop()`, `port`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `books_author` on `author COLLATE NOCASE`.
