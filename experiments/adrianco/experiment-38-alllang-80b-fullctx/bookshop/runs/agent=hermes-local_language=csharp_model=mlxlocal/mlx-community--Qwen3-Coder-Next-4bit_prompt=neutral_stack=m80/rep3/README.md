# Book API REST Service

A REST API service for managing a book collection built with C# and .NET 8, using SQLite for data storage.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- .NET 8.0 SDK or later
- SQLite (included via NuGet package)

## Setup

1. Clone or copy the project files to your working directory

2. Restore dependencies:
```bash
dotnet restore
```

3. Build the project:
```bash
dotnet build
```

## Running the Application

### Development Mode
```bash
dotnet run
```

The API will be available at `https://localhost:5001` (or the port shown in the console output).

### With Swagger UI
The application includes Swagger/OpenAPI documentation accessible at:
- `/swagger` - Swagger UI
- `/openapi/v1.json` - OpenAPI JSON

## Running Tests

### Run all tests:
```bash
dotnet test
```

### Run specific test project:
```bash
dotnet test BookApi.Tests/BookApi.Tests.csproj
```

### Run specific test:
```bash
dotnet test --filter "FullyQualifiedName~BookRepositoryTests"
```

## API Usage Examples

### Create a Book
```bash
curl -X POST https://localhost:5001/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Pragmatic Programmer",
    "author": "David Thomas",
    "year": 1999,
    "isbn": "978-0201616224"
  }'
```

### Get All Books
```bash
curl https://localhost:5001/books
```

### Get All Books by Author
```bash
curl "https://localhost:5001/books?author=David%20Thomas"
```

### Get Book by ID
```bash
curl https://localhost:5001/books/1
```

### Update a Book
```bash
curl -X PUT https://localhost:5001/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Pragmatic Programmer (Updated)",
    "author": "David Thomas",
    "year": 1999,
    "isbn": "978-0201616224"
  }'
```

### Delete a Book
```bash
curl -X DELETE https://localhost:5001/books/1
```

### Health Check
```bash
curl https://localhost:5001/health
```

## Project Structure

```
.
├── BookApi.csproj              # Main project file
├── Program.cs                  # Application entry point
├── Models/
│   └── Book.cs                 # Book domain model
├── Data/
│   └── BookRepository.cs       # Data access layer with SQLite
├── DTOs/
│   └── BookDto.cs              # Data Transfer Objects
├── Validators/
│   └── BookValidator.cs        # FluentValidation rules
├── Endpoints/
│   ├── BookEndpoints.cs        # Book API endpoints
│   └── HealthEndpoints.cs      # Health check endpoint
├── Tests/
│   ├── Unit/
│   │   ├── BookValidatorTests.cs
│   │   ├── BookRepositoryTests.cs
│   │   └── BookDtoTests.cs
│   └── Integration/
│       └── BookApiIntegrationTest.cs
├── BookApi.Tests/
│   └── BookApi.Tests.csproj    # Test project
└── README.md
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Validation error or invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Configuration

The SQLite database file location can be configured via the connection string in `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "Default": "Data Source=books.db"
  }
}
```

## License

MIT License
