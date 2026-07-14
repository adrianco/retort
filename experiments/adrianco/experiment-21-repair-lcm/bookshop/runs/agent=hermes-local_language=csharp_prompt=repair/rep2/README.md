# Book Manager API

A RESTful API for managing a book collection built with ASP.NET Core Web API and SQLite.

## Requirements

- .NET 10 SDK
- SQLite (provided via NuGet packages)

## Project Structure

```
BookManager/                 # Main web API project
  Models/
    Book.cs                  # Book entity and request DTOs
  Data/
    BookDbContext.cs         # EF Core DbContext for SQLite
  Controllers/
    BooksController.cs       # CRUD controller for books
  Program.cs                 # Application entry point and DI setup
BookManager.Tests/           # xUnit integration tests
  BookApiTests.cs            # 12 integration tests
```

## Setup

```bash
# Restore packages
dotnet restore

# Build the project
dotnet build

# Run the API
dotnet run --project BookManager/BookManager.csproj
```

The API will start on `http://localhost:5000` by default.

## API Endpoints

### Health Check
- `GET /health` - Returns 200 OK if the service is running

### Books
- `POST /books` - Create a new book
- `GET /books` - Get all books (supports `?author=` query filter)
- `GET /books/{id}` - Get a book by ID
- `PUT /books/{id}` - Update an existing book
- `DELETE /books/{id}` - Delete a book

### Request/Response Example

Create a book:
```http
POST /books
Content-Type: application/json

{
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "year": 2008,
  "isbn": "978-0132350884"
}
```

Response:
```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "year": 2008,
  "isbn": "978-0132350884"
}
```

### Validation Rules

- `title` and `author` are required fields
- Missing or empty title/author returns HTTP 400 Bad Request
- Non-existent book IDs return HTTP 404 Not Found
- Successful create returns HTTP 201 Created
- Successful delete returns HTTP 204 No Content

## Running Tests

```bash
dotnet test BookManager.Tests/BookManager.Tests.csproj
```

There are 12 integration tests covering:

- **CreateBook_ReturnsCreated_WithValidData** - Verifies POST creates a book
- **CreateBook_ReturnsBadRequest_WhenTitleMissing** - Validates title required
- **CreateBook_ReturnsBadRequest_WhenAuthorMissing** - Validates author required
- **GetBooks_ReturnsAllBooks** - Lists all books
- **GetBooks_FilterByAuthor_ReturnsMatchingBooks** - Tests author query filter
- **GetBookById_ReturnsBook_WhenExists** - Gets a single book
- **GetBookById_ReturnsNotFound_WhenMissing** - Returns 404 for missing book
- **UpdateBook_ReturnsOk_WithValidData** - Updates an existing book
- **UpdateBook_ReturnsNotFound_WhenMissing** - Returns 404 for update on missing book
- **DeleteBook_ReturnsNoContent_WhenExists** - Deletes a book successfully
- **DeleteBook_ReturnsNotFound_WhenMissing** - Returns 404 for delete of missing book
- **HealthCheck_ReturnsSuccess** - Health endpoint returns 200

Tests use `WebApplicationFactory` with an isolated in-memory SQLite database (shared cache mode) for fast, independent test execution.
