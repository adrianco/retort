# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | `/health` | `200 {"status":"healthy"}` | `main.go:53 healthCheck` |
| GET | `/books` | `200 [Book]` (or `null` when empty) | `main.go:60 getBooks` |
| GET | `/books?author=X` | `200 [Book]` filtered by `author LIKE '%X%'` | `main.go:60 getBooks` |
| POST | `/books` | `201 Book` \| `400` | `main.go:123 createBook` |
| GET | `/books/{id}` | `200 Book` \| `400` \| `404` | `main.go:96 getBook` |
| PUT | `/books/{id}` | `200 Book` \| `400` \| `404` | `main.go:158 updateBook` |
| DELETE | `/books/{id}` | `200 {"message":...}` \| `400` \| `404` | `main.go:207 deleteBook` |
| any other | `/books`, `/books/` | `405` | `main.go:249`, `main.go:260` |

Routing is `net/http`'s `DefaultServeMux` with two patterns (`/books`, `/books/`) and a hand-rolled `switch r.Method` in each closure. No third-party router.

## Data schema

`books` table (`main.go:38`), SQLite file `./books.db`:

`id` INTEGER PRIMARY KEY AUTOINCREMENT · `title` TEXT NOT NULL · `author` TEXT NOT NULL · `year` INTEGER · `isbn` TEXT

## Library API

`(none)` — `package main`, nothing exported for reuse.

## CLI commands

`(none)` — the binary takes no flags; `PORT` env var overrides the default `8080` (`main.go:274`).
