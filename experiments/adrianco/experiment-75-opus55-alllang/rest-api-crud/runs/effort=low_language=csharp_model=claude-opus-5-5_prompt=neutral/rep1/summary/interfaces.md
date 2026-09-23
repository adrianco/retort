# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `Program.cs:8` |
| POST | /books | `201 Book \| 400` | `Program.cs:10` |
| GET | /books | `200 [Book]` (optional `?author=`) | `Program.cs:18` |
| GET | /books/{id:long} | `200 Book \| 404` | `Program.cs:20` |
| PUT | /books/{id:long} | `200 Book \| 400 \| 404` | `Program.cs:23` |
| DELETE | /books/{id:long} | `204 \| 404` | `Program.cs:30` |

## Data schema

`books` table (`Program.cs:63`): `id` (INTEGER pk autoincrement), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `Book(long Id, string Title, string Author, int? Year, string? Isbn)` — record returned by the API.
- `BookInput(string? Title, string? Author, int? Year, string? Isbn)` — request body; `Validate()` returns problem-details errors (title/author required, year 0–9999).
- `BookRepository` — `Create`, `List(author?)`, `Get(id)`, `Update(id, input)`, `Delete(id)`; opens a new `SqliteConnection` per call, keeps a shared in-memory DB alive when the connection string is in-memory.
