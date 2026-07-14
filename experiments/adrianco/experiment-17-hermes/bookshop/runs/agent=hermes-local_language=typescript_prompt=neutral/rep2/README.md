# Book API REST Service

A REST API for managing a book collection with SQLite database backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Node.js (v14 or higher)
- npm

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Start the server:
   ```
   npm start
   ```

## Development

To run in development mode:
```
npm run dev
```

## Database

The application uses SQLite database (`books.db`) to store book data. The database is automatically created when the application starts.

## Testing

The application includes unit and integration tests. Run tests with:
```
npm test
```

Tests cover:
- Book creation and validation
- Book retrieval by ID and all books
- Book filtering by author
- Book updates
- Book deletion
- API endpoint responses

## Implementation Details

This REST API implements all required endpoints:
- POST /books - Create a new book with title, author, year, and isbn
- GET /books - List all books with optional ?author= filter
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

The implementation includes:
- Input validation (title and author are required)
- SQLite database storage
- Proper HTTP status codes
- Error handling for all endpoints
- JSON responses
