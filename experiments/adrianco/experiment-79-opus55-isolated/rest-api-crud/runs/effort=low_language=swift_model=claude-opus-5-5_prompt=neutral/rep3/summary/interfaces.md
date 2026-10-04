# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `Router.swift:24` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `Router.swift:33` |
| POST | /books | `201 Book` + `Location` header / `400` malformed / `422` invalid | `Router.swift:36` |
| GET | /books/{id} | `200 Book \| 404` | `Router.swift:56` |
| PUT | /books/{id} | `200 Book \| 404 \| 400 \| 422` | `Router.swift:59` |
| DELETE | /books/{id} | `204 \| 404` | `Router.swift:64` |

Unknown methods on a matched path return `405` with an `Allow` header; unknown paths return `404`.

## Library API (module BookAPI)

- `BookStore(path:)` — `create/list(author:)/get(id:)/update(id:)/delete(id:)`
- `Router(store:)` — `handle(HTTPRequest) -> HTTPResponse`
- `Server(router:)` — `start(port:) -> UInt16`, `stop()`
- `HTTPRequest.parse(Data) -> ParseResult`, `HTTPResponse.json/error/serialized`
- `BookInput.parse(Data) -> ParseResult` (`.valid/.malformed/.invalid([String])`)

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). All queries use bound parameters.
