# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"healthy"}` | Program.cs:20 |
| POST | /books | `201 Book \| 400 ValidationProblem` | Program.cs:23 |
| GET | /books | `200 [Book]` (optional `?author=` filter) | Program.cs:46 |
| GET | /books/{id:int} | `200 Book \| 404` | Program.cs:59 |
| PUT | /books/{id:int} | `200 Book \| 400 \| 404` | Program.cs:66 |
| DELETE | /books/{id:int} | `204 \| 404` | Program.cs:90 |

## CLI commands

(none)

## Library API

- `BookApi.Models.Book` — entity: `Id`, `Title`, `Author`, `Year?`, `Isbn?`
- `BookApi.Models.BookInput` — record DTO: `Title?`, `Author?`, `Year?`, `Isbn?`
- `BookApi.Data.BookDbContext` — EF Core context exposing `DbSet<Book> Books`

## Data schema

`Books` table (EF Core `EnsureCreated`): Id (int, pk, identity), Title (str, non-null),
Author (str, non-null), Year (int, nullable), Isbn (str, nullable). SQLite storage,
default `Data Source=books.db`.
