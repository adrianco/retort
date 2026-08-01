# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"healthy"}` | Program.cs (inline) |
| POST | /books | `201 Book` / `400 ValidationProblem` | Program.cs → `BookRepository.CreateAsync` |
| GET | /books?author= | `200 [Book]` | Program.cs → `BookRepository.GetAllAsync` |
| GET | /books/{id:int} | `200 Book` / `404` | Program.cs → `BookRepository.GetByIdAsync` |
| PUT | /books/{id:int} | `200 Book` / `400 ValidationProblem` / `404` | Program.cs → `BookRepository.UpdateAsync` |
| DELETE | /books/{id:int} | `204` / `404` | Program.cs → `BookRepository.DeleteAsync` |

Notes:
- `POST` and `PUT` validate that `title` and `author` are non-blank; failure returns an RFC 7807 `ValidationProblem` (400) keyed by `title`/`author`.
- The `?author=` filter is a case-preserving `LIKE %value%` substring match (SQLite `LIKE` is case-insensitive for ASCII).
- `{id}` is constrained to `int`; non-integer ids fall through to 404 (no matching route).

## Library API

`BookRepository(string connectionString)` — sealed class. Public async methods: `InitializeAsync()`, `CreateAsync(BookInput)`, `GetAllAsync(string? author = null)`, `GetByIdAsync(int)`, `UpdateAsync(int, BookInput)`, `DeleteAsync(int)`.

## Data schema

`Books` table: `Id` (INTEGER PK AUTOINCREMENT), `Title` (TEXT NOT NULL), `Author` (TEXT NOT NULL), `Year` (INTEGER NULL), `Isbn` (TEXT NULL).

Records: `Book(int Id, string Title, string Author, int? Year, string? Isbn)`; `BookInput(string? Title, string? Author, int? Year, string? Isbn)`.

## CLI commands

(none)
