# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `Router.swift:route` (health case) |
| GET | /books | `200 [Book]` (supports `?author=` filter, case-insensitive) | `Router.swift:route` → `store.list` |
| POST | /books | `201 Book` + `Location` header, `400` on validation error | `Router.swift:route` → `store.create` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` (bad id) | `Router.swift:route` → `store.get` |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `Router.swift:route` → `store.update` |
| DELETE | /books/{id} | `204` \| `404` | `Router.swift:route` → `store.delete` |

Unmatched methods return `405` with an `Allow` header; unknown paths `404`.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

`BookStore(path:)`, `Router(store:)`, `Server(router:port:loopbackOnly:)`,
`HTTPParser.parse(_:)`, `BookInput.parse(json:)`.
