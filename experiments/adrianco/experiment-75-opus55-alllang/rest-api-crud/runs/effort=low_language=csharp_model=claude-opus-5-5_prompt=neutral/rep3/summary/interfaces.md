# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `Program.cs:8` |
| POST | /books | `201 Book` / `400 {errors}` | `Program.cs:10` |
| GET | /books?author= | `200 [Book]` (optional author filter) | `Program.cs:18` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `Program.cs:20` |
| PUT | /books/{id} | `200 Book` / `400 {errors}` / `404 {error}` | `Program.cs:23` |
| DELETE | /books/{id} | `204` / `404 {error}` | `Program.cs:30` |

## Data schema

`books` table (SQLite, `Program.cs:63`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `record Book(long Id, string Title, string Author, int? Year, string? Isbn)`
- `record BookInput(string? Title, string? Author, int? Year, string? Isbn)` with `List<string> Validate()`
- `class BookRepository`: `Create`, `List(author?)`, `Get(id)`, `Update(id, input)`, `Delete(id)`
