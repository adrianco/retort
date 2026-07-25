# Book API REST Service

A REST API service for managing a book collection built with ASP.NET Core and SQLite.

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

1. Clone or navigate to the project directory

2. Restore dependencies:
```bash
dotnet restore
```

3. Build the project:
```bash
dotnet build
```

## Running the Application

```bash
dotnet run
```

The API will start on port 5000 (HTTP) or 5001 (HTTPS) by default.

## API Usage Examples

### Health Check
```bash
curl http://localhost:5000/health
```

### Create a Book
```bash
curl -X POST http://localhost:5000/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List All Books
```bash
curl http://localhost:5000/api/books
```

### List Books by Author
```bash
curl "http://localhost:5000/api/books?author=George%20Orwell"
```

### Get Book by ID
```bash
curl http://localhost:5000/api/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:5000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "978-0451524935"
  }'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:5000/api/books/1
```

## Testing

Run the tests with:
```bash
dotnet test
```

## Project Structure

- `Models/Book.cs` - Book entity model
- `Data/BookDbContext.cs` - Entity Framework Core database context
- `Controllers/BooksController.cs` - API controllers for book operations
- `Program.cs` - Application entry point and configuration

## Database

The application uses SQLite and stores data in a file named `books.db` in the application directory.
