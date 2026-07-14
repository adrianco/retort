# Interfaces

## HTTP routes

| Method | Path | Returns | Handler (wired in `main()`) |
|--------|------|---------|------------------------------|
| GET | /health | `{status} \| 500` | `main.go:handleHealthCheck` |
| GET | /books | `[Book]` (200) | `main.go:handleGetBooks` |
| POST | /books | `Book` (201) \| 400 | `main.go:handleCreateBook` |
| GET | /books/{id} | `Book` (200) \| 400 \| 404 | `main.go:handleGetBookWithID` |
| PUT | /books/{id} | `{message}` (200) \| 400 | `main.go:handleUpdateBookWithID` |
| DELETE | /books/{id} | `{message}` (200) | `main.go:handleDeleteBookWithID` |

`GET /books` supports an `?author=` query param (SQL `LIKE %author%` substring match).

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`BookStore` exported methods: `NewBookStore(dbPath)`, `Close()`, `CreateBook`, `GetBooks(author)`, `GetBook(id)`, `UpdateBook(id, book)`, `DeleteBook(id)`, `HealthCheck()`.
