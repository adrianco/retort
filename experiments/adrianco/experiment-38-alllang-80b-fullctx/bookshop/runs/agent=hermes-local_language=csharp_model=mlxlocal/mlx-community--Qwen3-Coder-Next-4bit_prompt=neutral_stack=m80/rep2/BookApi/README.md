# Book API REST Service

A REST API service for managing a book collection using ASP.NET Core with SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- .NET 10.0 SDK or later
- SQLite (included as NuGet package)

## Setup

1. Navigate to the BookApi directory:

```bash
cd BookApi
```

2. Build the project:

```bash
dotnet build
```

3. Run the application:

```bash
dotnet run
```

The API will start on `https://localhost:7043` (or another port if 7043 is in use).

## API Endpoints

### Health Check

```
GET /api/health
```

Response:
```json
{
  "status": "healthy"
}
```

### Get All Books

```
GET /api/books
```

With author filter:
```
GET /api/books?author=Martin
```

### Get Book by ID

```
GET /api/books/{id}
```

### Create Book

```
POST /api/books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890"
}
```

### Update Book

```
PUT /api/books/{id}
Content-Type: application/json

{
  "id": 1,
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "1234567890"
}
```

### Delete Book

```
DELETE /api/books/{id}
```

## Running Tests

Run all tests:

```bash
cd BookApi.Tests
dotnet test
```

Run specific test file:

```bash
dotnet test --filter "FullyQualifiedName~BooksControllerTests"
```

## Project Structure

```
BookApi/
├── Controllers/
│   ├── BooksController.cs
│   └── HealthController.cs
├── Data/
│   └── BookDbContext.cs
├── Models/
│   └── Book.cs
├── Program.cs
├── BookApi.csproj
└── appsettings.json
BookApi.Tests/
├── Unit/
│   └── BooksControllerTests.cs
├── Integration/
│   ├── BookApiIntegrationFixture.cs
│   ├── BooksControllerTests.cs
│   └── HealthControllerTests.cs
├── MockDbSetExtensions.cs
├── BookApi.Tests.csproj
└── appsettings.json
```

## Database

The API uses SQLite as the database. The database file `books.db` is created in the application directory when the application runs.

For tests, a temporary SQLite database is created and destroyed for each test run.
