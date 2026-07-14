# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: "ok"}` | `app.go:HealthCheck` |
| POST | /books | `201 Book` / `400 {error}` / `500 {error}` | `app.go:CreateBook` |
| GET | /books | `200 [Book]` (supports `?author=` filter) | `app.go:ListBooks` |
| GET | /books/:id | `200 Book` / `400` / `404` / `500` | `app.go:GetBook` |
| PUT | /books/:id | `200 Book` / `400` / `404` / `500` | `app.go:UpdateBook` |
| DELETE | /books/:id | `200 {message}` / `400` / `404` / `500` | `app.go:DeleteBook` |

## Library API

Exported symbols (package `main`):

- `Book` — entity struct: `ID int`, `Title string`, `Author string`, `Year int`, `ISBN string`.
- `CreateBookRequest` — request body for create/update: `Title`, `Author`, `Year`, `ISBN`.
- `Database` — wraps `*sql.DB`.
- `NewDatabase(dbPath string) (*Database, error)` — opens SQLite and ensures the `books` table exists.
- Handler methods on `*Database`: `CreateBook`, `ListBooks`, `GetBook`, `UpdateBook`, `DeleteBook`; plus free function `HealthCheck`.

## Data schema

`books` table (SQLite):

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL |
| isbn | TEXT | NOT NULL |

## CLI commands

(none) — single server binary listening on `:8080`; DB file hardcoded to `books.db`.

## Validation notes

Title and author are checked non-empty in both `CreateBook` and `UpdateBook`. `year` and `isbn` are not validated; all four columns are `NOT NULL` at the DB level but omitted JSON fields default to zero/empty and still insert.
