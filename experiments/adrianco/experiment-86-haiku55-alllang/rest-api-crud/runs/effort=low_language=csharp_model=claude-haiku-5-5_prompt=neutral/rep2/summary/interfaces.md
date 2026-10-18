# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `Program.cs` inline |
| POST | /books | `201 Book` / `400` | `Program.cs` inline (`repo.CreateAsync`) |
| GET | /books | `200 [Book]` | `Program.cs` inline (`repo.ListAsync`) |
| GET | /books?author= | `200 [Book]` (case-insensitive exact match) | `Program.cs` inline |
| GET | /books/{id:long} | `200 Book` / `404` | `Program.cs` inline (`repo.GetAsync`) |
| PUT | /books/{id:long} | `200 Book` / `400` / `404` | `Program.cs` inline (`repo.UpdateAsync`) |
| DELETE | /books/{id:long} | `204` / `404` | `Program.cs` inline (`repo.DeleteAsync`) |

Validation failures return an RFC 7807 `ValidationProblem` (400) with a field-level `errors` map. Unknown IDs return `404 {error}`.

## Library API

- `IBookRepository` — `ListAsync(author?)`, `GetAsync(id)`, `CreateAsync(input)`, `UpdateAsync(id, input)`, `DeleteAsync(id)`
- `BookValidator.Validate(BookInput, now?)` → `Dictionary<string,string[]>`; `BookValidator.IsValidIsbn(string)`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NULL), `isbn` (TEXT NULL).
