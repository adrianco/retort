# Interfaces

## HTTP routes

All routes are registered under an `/api` group in `main()` (`app.go:329`).
The spec (TASK.md) and the tests use the bare paths shown in parentheses.

| Method | Path (served) | Spec path | Returns | Handler |
|--------|---------------|-----------|---------|---------|
| GET | /api/health | /health | `{status,timestamp,database}` | `app.go:HealthCheck` |
| GET | /api/books | /books | `[Book]` | `app.go:GetBooks` |
| GET | /api/books?author= | /books?author= | `[Book]` filtered | `app.go:GetBooks` |
| POST | /api/books | /books | `Book \| 400` | `app.go:CreateBook` |
| GET | /api/books/:id | /books/{id} | `Book \| 400 \| 404` | `app.go:GetBook` |
| PUT | /api/books/:id | /books/{id} | `Book \| 400 \| 404` | `app.go:UpdateBook` |
| DELETE | /api/books/:id | /books/{id} | `{message} \| 404` | `app.go:DeleteBook` |

## Data schema

`books` table (SQLite, `./books.db`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER NOT NULL), isbn (TEXT NOT NULL).

`BookInput` binding tags mark title, author, **year, and isbn** all `required`.
