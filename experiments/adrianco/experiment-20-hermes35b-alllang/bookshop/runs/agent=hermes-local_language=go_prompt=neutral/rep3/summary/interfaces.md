# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` 201 / 400 / 409 / 500 | `main.go:createBook` |
| GET | /books | `[Book]` 200 (supports `?author=`) | `main.go:listBooks` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `main.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `main.go:updateBook` |
| DELETE | /books/{id} | 204 (no content) | `main.go:deleteBook` |
| GET | /health | `{"status":"healthy"}` 200 | inline closure in `main()` |

Routing: `mux.Handle("/books", store)` for the collection, `mux.HandleFunc("/books/", store.ServeHTTP)` for item paths; `(*BookStore).ServeHTTP` trims the `/books` prefix and dispatches by method + remaining path.

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER NOT NULL), isbn (TEXT NOT NULL UNIQUE). SQLite via `modernc.org/sqlite` (pure-Go, no cgo), WAL journal mode, `:memory:` database.

## Library API

`NewBookStore(dbPath)`, `(*BookStore)` methods: `CreateBook`, `GetBookByID`, `ListBooks(authorFilter)`, `UpdateBook`, `DeleteBook`, `Close`.
