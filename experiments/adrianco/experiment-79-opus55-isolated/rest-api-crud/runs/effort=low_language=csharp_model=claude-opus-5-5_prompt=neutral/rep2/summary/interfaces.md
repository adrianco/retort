# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | Program.cs:11 |
| POST | /books | `201 Book \| 400` | Program.cs:13 |
| GET | /books | `200 [Book]` (optional `?author=`) | Program.cs:23 |
| GET | /books/{id} | `200 Book \| 404` | Program.cs:25 |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | Program.cs:28 |
| DELETE | /books/{id} | `204 \| 404` | Program.cs:37 |

## Library API

- `BookStore.List(string? author)`, `Get(long)`, `Create(BookInput)`, `Update(long, BookInput)`, `Delete(long)`
- `BookInput.Validate()` → `Dictionary<string,string[]>` of field errors

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
