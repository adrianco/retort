# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `Router.swift` health case |
| POST | /books | `201 Book` (+ `Location`) / `400` | `Router.swift:createBook` |
| GET | /books | `200 [Book]`; `?author=` exact, case-insensitive | `Router.swift:listBooks` |
| GET | /books/{id} | `200 Book` / `404` | `Router.swift:getBook` |
| PUT | /books/{id} | `200 Book` (full replace) / `400` / `404` | `Router.swift:updateBook` |
| DELETE | /books/{id} | `204` / `404` | `Router.swift:deleteBook` |

Unsupported methods on a known path return `405` with an `Allow` header; unknown
paths and non-numeric ids return `404`; oversized bodies `413`; malformed requests `400`.

## Library API

`BookStore` (SQLite CRUD), `BookRouter.handle(HTTPRequest) -> HTTPResponse`,
`HTTPServer.start(port:)`, `BookValidator.validate(_:)`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
