# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"healthy"}` | `Program.cs` MapGet /health |
| POST | /books | `201 Book` / `400 {error}` | `Program.cs` MapPost /books |
| GET | /books | `200 [Book]` (optional `?author=` exact-match filter) | `Program.cs` MapGet /books |
| GET | /books/{id:int} | `200 Book` / `404` | `Program.cs` MapGet /books/{id} |
| PUT | /books/{id:int} | `200 Book` / `400 {error}` / `404` | `Program.cs` MapPut /books/{id} |
| DELETE | /books/{id:int} | `204` / `404` | `Program.cs` MapDelete /books/{id} |

## Data schema

`Books` table (EF Core `Book` entity): Id (int, pk, identity), Title (string), Author (string), Year (int), Isbn (string). Persisted to SQLite (`Data Source=books.db` by default; connection string `BookDb` overridable).

## Request DTO

`BookCreateRequest(Title, Author, Year, Isbn)` — shared by POST and PUT. `IsValid(out error)` rejects blank/whitespace Title or Author with `400`.
