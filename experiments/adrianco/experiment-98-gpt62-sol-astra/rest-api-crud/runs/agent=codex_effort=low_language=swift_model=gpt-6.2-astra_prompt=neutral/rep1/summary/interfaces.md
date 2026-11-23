# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `Books.swift:route` |
| POST | /books | 201 `Book` \| 400 | `Books.swift:route` → `Database.save` |
| GET | /books | 200 `[Book]` (optional `?author=` filter) | `Books.swift:route` → `Database.list` |
| GET | /books/{id} | 200 `Book` \| 404 | `Books.swift:route` → `Database.get` |
| PUT | /books/{id} | 200 `Book` \| 400 \| 404 | `Books.swift:route` → `Database.save` |
| DELETE | /books/{id} | 200 `{"deleted":id}` \| 404 | `Books.swift:route` → `Database.delete` |

Unknown routes return 404; unsupported method/target combinations return 405. Oversized
bodies return 413; malformed HTTP returns 400; `Transfer-Encoding` returns 501.

## Data schema

`books` table (SQLite): `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `author` (TEXT NOT NULL,
denormalized for the `?author=` filter), `document` (TEXT NOT NULL — JSON blob of the full
`Fields`: title, author, optional year, optional isbn).

## Library API (exposed via `@testable import BooksAPI`)

- `route(_ method: String, _ target: String, _ body: Data, db: Database) throws -> (Int, Data)`
- `serve(_ fd: Int32, db: Database)`
- `Database(path:)` with `list(author:)`, `get(_:)`, `save(_:id:)`, `delete(_:)`
- `Fields` (Codable), `Book` (Encodable), `APIError`
