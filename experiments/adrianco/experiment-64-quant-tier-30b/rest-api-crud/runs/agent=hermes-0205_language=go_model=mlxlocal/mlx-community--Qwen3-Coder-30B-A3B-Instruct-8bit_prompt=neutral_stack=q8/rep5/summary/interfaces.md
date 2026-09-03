# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"healthy"}` | `main.go:49 healthHandler` |
| POST | /books | `201 Book` \| `400` \| `500` | `main.go:56 createBookHandler` |
| GET | /books | `200 [Book]` (`?author=` substring filter) | `main.go:95 getBooksHandler` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:136 getBookHandler` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:170 updateBookHandler` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `main.go:230 deleteBookHandler` |

Routing is `http.NewServeMux` with two patterns (`/books`, `/books/`) plus `/health`; the
method is dispatched inside each closure (`main.go:288-315`). Non-matching methods get `405`.

## CLI commands

(none) — the binary takes no flags; it listens on a hard-coded `:8080`.

## Library API

(none) — `package main`, nothing exported.

## Data schema

`books` table in `./books.db` (`main.go:34-41`):
`id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL,
`year` INTEGER, `isbn` TEXT.
