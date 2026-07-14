# Book API

A REST API for managing a book collection, built with ASP.NET Core and EF Core over SQLite.

## Stack

- C# / ASP.NET Core Web API (.NET 10)
- Entity Framework Core with SQLite (embedded database)
- xUnit + `Microsoft.AspNetCore.Mvc.Testing` for BDD-style integration tests

## Project layout

```
BookApi.slnx
src/BookApi/            # API project
  Controllers/           # BooksController, HealthController
  Models/                # Book entity
  Dtos/                  # Request/response DTOs with validation
  Data/                  # BookDbContext (EF Core)
  Program.cs
tests/BookApi.Tests/     # Integration tests (Given/When/Then)
```

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download)

## Setup & run

```bash
# restore & build everything
dotnet build BookApi.slnx

# run the API (listens on the default ASP.NET Core Kestrel URLs, e.g. http://localhost:5099)
dotnet run --project src/BookApi
```

On startup, the app creates a local SQLite database file (`books.db`, in the project's working
directory) and applies the schema automatically — no separate migration step required.

To use a different database location, set the `ConnectionStrings:BookDb` configuration value
(e.g. via `appsettings.json`, an environment variable, or `--ConnectionStrings:BookDb="Data Source=/path/to/books.db"`).

## Run tests

```bash
dotnet test BookApi.slnx
```

Tests spin up the full API in-process (`WebApplicationFactory`) against an isolated in-memory
SQLite database, so no external services or files are required.

## API

### Health check

```
GET /health
```

Returns `200 OK` with `{ "status": "healthy" }`.

### Books

| Method | Path              | Description                          |
|--------|-------------------|---------------------------------------|
| POST   | `/books`          | Create a new book                     |
| GET    | `/books`          | List all books (optional `?author=` filter) |
| GET    | `/books/{id}`     | Get a single book by ID                |
| PUT    | `/books/{id}`     | Update an existing book                |
| DELETE | `/books/{id}`     | Delete a book                          |

Book request/response body:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

`title` and `author` are required on create/update; omitting or blanking either returns
`400 Bad Request` with validation details. `year` and `isbn` are optional.

### Example requests

```bash
# Create a book
curl -X POST http://localhost:5099/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List all books
curl http://localhost:5099/books

# Filter by author
curl "http://localhost:5099/books?author=Frank"

# Get one book
curl http://localhost:5099/books/1

# Update a book
curl -X PUT http://localhost:5099/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete a book
curl -X DELETE http://localhost:5099/books/1
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST (includes `Location` header)
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (e.g. missing title/author)
- `404 Not Found` — book with the given ID doesn't exist
