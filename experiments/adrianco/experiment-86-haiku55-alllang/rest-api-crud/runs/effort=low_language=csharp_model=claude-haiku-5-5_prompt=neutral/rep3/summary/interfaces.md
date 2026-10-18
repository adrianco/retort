# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"Healthy"}` / `503 {status:"Unhealthy"}` | `Program.cs` (pings DB via `repo.PingAsync`) |
| POST | /books | `201 Book` / `400 ValidationProblem` | `Program.cs` → `repo.CreateAsync` |
| GET | /books | `200 [Book]` (optional `?author=`) | `Program.cs` → `repo.ListAsync` |
| GET | /books/{id:long} | `200 Book` / `404` | `Program.cs` → `repo.GetAsync` |
| PUT | /books/{id:long} | `200 Book` / `400` / `404` | `Program.cs` → `repo.UpdateAsync` |
| DELETE | /books/{id:long} | `204` / `404` | `Program.cs` → `repo.DeleteAsync` |

## Library API

`IBookRepository`: `ListAsync(author)`, `GetAsync(id)`, `CreateAsync(req)`, `UpdateAsync(id, req)`, `DeleteAsync(id)`, `PingAsync()`.
`BookValidator.Validate(BookRequest)` → `Dictionary<string,string[]>` of field errors.

## Data schema

`books` table: `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER NULL, `isbn` TEXT NULL. `?author=` matches exactly, case-insensitive (`COLLATE NOCASE`).
