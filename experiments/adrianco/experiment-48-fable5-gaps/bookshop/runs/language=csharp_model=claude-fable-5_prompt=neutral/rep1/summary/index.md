# Architecture Summary — BookApi (C#, .NET 10)

ASP.NET Core minimal-API REST service for a book collection, backed by SQLite.

## Modules

| File | Role |
|------|------|
| `BookApi/Program.cs` | App bootstrap + all six route handlers (`/health`, CRUD on `/books`). Registers `BookRepository` as a singleton; reads connection string from config (`ConnectionStrings:Books`, default `Data Source=books.db`). |
| `BookApi/Book.cs` | `Book` record (persisted shape) and `BookInput` record (request DTO) with `Validate()` returning a list of error strings (title/author required, year 0–9999). |
| `BookApi/BookRepository.cs` | SQLite data-access layer using `Microsoft.Data.Sqlite`. Creates the `books` table on construction; parameterised `Create/List/Get/Update/Delete`. `List` applies an optional `WHERE author = $author COLLATE NOCASE` filter. |
| `BookApi.Tests/BookApiTests.cs` | 11 xUnit integration tests via `WebApplicationFactory<Program>`, each fixture using a unique temp DB file. |

## Request flow

`HTTP → Program.cs minimal-API handler → BookInput.Validate() (write paths) → BookRepository (parameterised SQL) → SQLite → JSON result`.

## Notable choices

- Full-replace PUT semantics (all fields overwritten, re-validated).
- Correct status codes: 201 Created (+ Location), 200, 204 No Content, 400, 404.
- Tests exercised in-process against the real HTTP pipeline with an isolated on-disk SQLite DB per fixture.
- SQL injection safe — all queries parameterised.
