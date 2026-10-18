# Run Summary

ASP.NET Core minimal-API REST service for a book collection, backed by SQLite via
Entity Framework Core. One executable project (`BookCollection.Api`) plus one
integration-test project (`BookCollection.Tests`) using `WebApplicationFactory`.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `BookCollection.Api/Program.cs` | Minimal-API host: DI wiring, EnsureCreated, all routes, validation | top-level statements, `Validate()`, `BookInput` |
| `BookCollection.Api/Models/Book.cs` | EF entity | `Book` |
| `BookCollection.Api/Data/BookDbContext.cs` | EF Core DbContext | `BookDbContext`, `Books` |
| `BookCollection.Tests/BookApiTests.cs` | xUnit integration tests over the real app | 4 `[Fact]` methods |

## Interfaces (HTTP)

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/health` | `200 {status:"healthy"}` |
| POST | `/books` | `201` + Location on success; `400` ValidationProblem if title/author blank |
| GET | `/books` | `200` list; optional `?author=` case-insensitive filter; ordered by id |
| GET | `/books/{id:int}` | `200` book or `404` |
| PUT | `/books/{id:int}` | `200` updated book; `404` if absent; `400` if invalid |
| DELETE | `/books/{id:int}` | `204` or `404` |

## Data schema

`Book { Id:int (PK), Title:string (required), Author:string (required), Year:int?, Isbn:string? }`
persisted to SQLite (`Data Source=books.db`, overridable via `ConnectionStrings__Books`).

## Flow

Request → minimal-API handler → `BookDbContext` (EF Core, SQLite) → JSON result.
Validation runs before persistence on POST/PUT. Schema created at startup via
`Database.EnsureCreated()`.
