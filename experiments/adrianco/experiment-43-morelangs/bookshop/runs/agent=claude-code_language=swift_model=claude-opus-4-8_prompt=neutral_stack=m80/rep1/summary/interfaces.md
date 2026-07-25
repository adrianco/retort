# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `Router.swift:route` (health case) |
| GET | /books | `[Book] 200` | `Router.swift:routeBooks` |
| GET | /books?author= | `[Book] 200` (exact author match) | `Router.swift:routeBooks` → `BookStore.all(author:)` |
| POST | /books | `Book 201` / `400` | `Router.swift:createBook` |
| GET | /books/{id} | `Book 200` / `404` | `Router.swift:routeBooks` |
| PUT | /books/{id} | `Book 200` / `400` / `404` | `Router.swift:updateBook` |
| DELETE | /books/{id} | `204` / `404` | `Router.swift:routeBooks` |

Other status codes: `400` invalid JSON body or non-integer id, `405` method not allowed, `500` internal error.

## Library API

- `BookStore(path:)` — opens/creates a SQLite DB (`:memory:` supported); `create/all/get/update/delete`.
- `Router(store:)` — `route(HTTPRequest) -> HTTPResponse`.
- `HTTPServer(router:port:)` — `start(onReady:)`, `stop()`, `port`.
- `HTTPRequest.parse(Data) -> (request, complete)?`; `HTTPResponse.json/error/serialized`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
