# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `Program.cs:8` |
| POST | /books | `Book` (201) / validation problem (400) | `Program.cs:10` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `Program.cs:18` |
| GET | /books/{id:long} | `Book` (200) / `{error}` (404) | `Program.cs:20` |
| PUT | /books/{id:long} | `Book` (200) / 400 / 404 | `Program.cs:23` |
| DELETE | /books/{id:long} | 204 / 404 | `Program.cs:30` |

## Data schema

`books` table (SQLite): `id` (INTEGER pk autoincrement), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER nullable), `isbn` (TEXT nullable).

## Library API

- `record Book(long Id, string Title, string Author, int? Year, string? Isbn)`
- `record BookInput(string? Title, string? Author, int? Year, string? Isbn)` — `Validate()` returns per-field errors
- `class BookRepository` — `Create`, `List(author)`, `Get(id)`, `Update(id, input)`, `Delete(id)`
