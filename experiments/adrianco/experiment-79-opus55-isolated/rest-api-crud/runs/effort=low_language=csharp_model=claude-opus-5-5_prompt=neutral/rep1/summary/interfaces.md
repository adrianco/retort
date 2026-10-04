# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503 {status:unavailable}` | `Program.cs:27` |
| POST | /books | `201 Book` / `400 ValidationProblem` | `Program.cs:42` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `Program.cs:52` |
| GET | /books/{id:long} | `200 Book` / `404 {error}` | `Program.cs:54` |
| PUT | /books/{id:long} | `200 Book` / `400` / `404 {error}` | `Program.cs:57` |
| DELETE | /books/{id:long} | `204` / `404 {error}` | `Program.cs:66` |

Malformed/unparseable JSON bodies are caught by middleware (`Program.cs:14`) and returned as `400 {error}`.

## Library API

- `BookRepository` — `Create`, `List(author?)`, `Get(id)`, `Update(id, input)`, `Delete(id)`, `Ping()`
- `BookInput.Validate()` — returns field-keyed error dictionary

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
