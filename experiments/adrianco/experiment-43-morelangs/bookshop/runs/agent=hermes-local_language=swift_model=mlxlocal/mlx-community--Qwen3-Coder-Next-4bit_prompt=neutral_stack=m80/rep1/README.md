# Book API REST Service

A REST API service for managing a book collection built with Swift and Vapor.

## Features

- **POST /books** - Create a new book
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Swift 5.9 or later
- Vapor 4.80+

## Setup

1. Clone the repository (or navigate to the workspace directory)

2. Build the project:
```bash
swift build
```

3. Run the server:
```bash
swift run
```

The server will start on `http://127.0.0.1:8080`

## API Endpoints

### Health Check
```bash
GET /health
```

### Create Book
```bash
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "9780743273565"
}
```

Response: `201 Created`

### List Books
```bash
GET /books
GET /books?author=Author%20Name
```

Response: `200 OK` with array of books

### Get Single Book
```bash
GET /books/{id}
```

Response: `200 OK` or `404 Not Found`

### Update Book
```bash
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2023,
  "isbn": "9780000000000"
}
```

Response: `200 OK` or `404 Not Found`

### Delete Book
```bash
DELETE /books/{id}
```

Response: `204 No Content` or `404 Not Found`

## Validation

- `title` and `author` are required
- `year` must be a valid year (1000-2124)
- `isbn` must be 10 or 13 characters

## Testing

Run the tests with:
```bash
swift test
```

## Project Structure

```
Sources/
├── App/
│   ├── main.swift          # Application entry point
│   ├── Setup.swift         # Configuration and routes
│   ├── Book.swift          # Book model
│   ├── BookController.swift # API controllers
│   └── migrations/
│       └── CreateBook.swift # Database migration
Tests/
├── AppTests/
│   ├── BookControllerTests.swift
│   ├── BookCRUDTests.swift
│   └── HealthEndpointTests.swift
Config/
└── config.json
```

## License

MIT
