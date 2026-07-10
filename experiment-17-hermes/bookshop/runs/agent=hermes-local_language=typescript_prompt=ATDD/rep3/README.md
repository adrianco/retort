# Book API - REST Service

REST API service for managing a book collection with the following features:

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Requirements

- Built with TypeScript and Express.js
- Uses SQLite for embedded database storage
- Implements input validation (title and author are required)
- Returns JSON responses with appropriate HTTP status codes
- Includes a health check endpoint

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Build the project:
   ```
   npm run build
   ```

3. Start the server:
   ```
   npm start
   ```

4. Run tests:
   ```
   npm test
   ```

## Implementation Details

The service implements a complete REST API with:
- SQLite database for storing book records
- All required CRUD operations
- Input validation
- Proper HTTP status codes
- Health check endpoint

The implementation handles:
- Creating books with validation
- Retrieving books by ID or all books
- Filtering books by author
- Updating books
- Deleting books
- Error handling and appropriate status codes
