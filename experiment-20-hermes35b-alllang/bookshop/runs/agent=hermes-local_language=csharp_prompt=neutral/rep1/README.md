# Book API

A RESTful API for managing a collection of books, built with ASP.NET Core 10 and EF Core.

## Features

- **CRUD Operations**: Create, read, update, and delete books
- **Filtering**: Search books by author
- **Validation**: Title and author are required fields
- **In-Memory Database**: Uses SQLite for development/testing
- **Health Check**: Simple health endpoint

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | Get all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |
| GET | `/health` | Health check |

## Creating a Book

```http
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Required Fields
- `title` (string, required)
- `author` (string, required)

### Optional Fields
- `year` (integer)
- `isbn` (string)

## Building and Running

### Prerequisites

- .NET 10 SDK

### Build

```bash
dotnet build src/BookApi.csproj
```

### Run

```bash
dotnet run --project src/BookApi.csproj
```

### Tests

```bash
dotnet test Tests/Tests.csproj
```

## Project Structure

```
src/
  BookApi.csproj          # Main project (net10.0, Nullable/ImplicitUsings enabled)
  Program.cs              # Minimal API endpoints, DI, DB context setup
  Models/Book.cs          # Entity: Id, Title, Author, Year?, Isbn?
  Data/BookDbContext.cs   # EF Core DbContext with DbSet<Book>
  Dto/CreateBookDto.cs    # [Required] Title, Author; [StringLength] Title
  Dto/UpdateBookDto.cs    # Optional Title, Author, Year, Isbn
Tests/
  Tests.csproj            # xUnit project, references src/BookApi.csproj
  BookApiTests.cs         # Integration tests using WebApplicationFactory
README.md
```

## Testing Framework

Tests use:
- **xUnit** for the test framework
- **WebApplicationFactory** for integration testing
- **In-Memory Database** via `Microsoft.EntityFrameworkCore.InMemory`

## License

MIT
