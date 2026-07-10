# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | app.go:HealthCheck |
| GET | /books | `[Book]` (supports `?author=`) | app.go:listBooks |
| POST | /books | `201 Book` \| `400` \| `409` | app.go:createBook |
| GET | /books/{id} | `Book` \| `404` | app.go:getBook |
| PUT | /books/{id} | `Book` \| `400` \| `404` | app.go:updateBook |
| DELETE | /books/{id} | `204` \| `404` | app.go:deleteBook |

Routing is done with `net/http` `HandleFunc`; `/books/` (with trailing slash) dispatches to `handleBookByID`, `/books` to `handleBooks`. The `{id}` segment is parsed by stripping the `/books/` prefix and calling `strconv.Atoi`.

## Library API

- `App{Repo *BookRepository}` — handler holder.
- `Book{ID, Title, Author, Year, ISBN}` — JSON-tagged model with `Validate()`.
- `BookRepository` — `NewBookRepository(dbPath)`, `CreateBook`, `GetAllBooks(authorFilter)`, `GetBookByID(id)`, `UpdateBook`, `DeleteBook`, `Close`.

## Data schema

`books` table:

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL |
| isbn | TEXT | NOT NULL UNIQUE |

## CLI commands

(none)
