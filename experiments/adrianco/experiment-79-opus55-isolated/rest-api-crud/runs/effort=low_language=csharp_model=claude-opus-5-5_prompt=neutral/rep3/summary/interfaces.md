# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `Program.cs:13` |
| GET | /books | `200 [Book]` (optional `?author=`) | `Program.cs:15` |
| GET | /books/{id} | `200 Book \| 404` | `Program.cs:17` |
| POST | /books | `201 Book \| 400` | `Program.cs:20` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `Program.cs:28` |
| DELETE | /books/{id} | `204 \| 404` | `Program.cs:37` |

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NULL), `isbn` (TEXT NULL).

## Library API

- `BookRepository(connectionString)` — creates the table if absent; methods `List(author?)`, `Get(id)`, `Create(input)`, `Update(id, input)`, `Delete(id)`.
- `BookInput.Validate()` — returns per-field error dictionary (title/author required, year 0–9999).
