# Interfaces

## HTTP routes

Registered via Go 1.22+ method-aware `http.ServeMux` in `handlers.go:Routes`.

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.go:handleHealth` |
| POST | /books | `201 Book` / `400` | `handlers.go:handleCreateBook` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `handlers.go:handleListBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:handleGetBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:handleUpdateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:handleDeleteBook` |

Errors are returned as JSON `{"error": "..."}` with the appropriate status.

## Library API

- `Store` (store.go): `Create`, `List(author)`, `Get(id)`, `Update(id, b)`, `Delete(id)`, sentinel `ErrNotFound`.
- `Book` (models.go): fields `ID, Title, Author, Year, ISBN`; `Validate()` returns a slice of messages for missing `Title`/`Author`.

## Data schema

`books` table (created in `store.go:migrate`):
`id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Configuration

Env vars: `BOOKS_DB_PATH` (default `books.db`), `BOOKS_ADDR` (default `:8080`).
