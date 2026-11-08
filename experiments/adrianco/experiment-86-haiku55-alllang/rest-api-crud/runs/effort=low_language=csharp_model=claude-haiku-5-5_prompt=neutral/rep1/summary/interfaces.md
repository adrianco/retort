# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` (200, or 503 if DB unreachable) | `Program.cs` → `BookRepository.Ping` |
| POST | /books | `Book` (201 Created + Location, or 400 problem+json) | `Program.cs` → `BookRepository.Add` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `Program.cs` → `BookRepository.List` |
| GET | /books/{id:long} | `Book` (200) or 404 | `Program.cs` → `BookRepository.Get` |
| PUT | /books/{id:long} | `Book` (200), 400 problem+json, or 404 | `Program.cs` → `BookRepository.Update` |
| DELETE | /books/{id:long} | 204 No Content or 404 | `Program.cs` → `BookRepository.Delete` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NULL).

## Validation rules

- `title`, `author` — required (non-blank).
- `year` — required, between 1450 and next calendar year.
- `isbn` — optional; if present, must match ISBN-10/13 after stripping hyphens/spaces; stored normalised to bare digits.
