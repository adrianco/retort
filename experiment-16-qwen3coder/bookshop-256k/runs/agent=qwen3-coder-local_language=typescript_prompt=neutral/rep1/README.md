# Book API

A REST API service for managing a book collection.

## Features
- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Run the server:
   ```
   npm start
   ```

3. Run tests:
   ```
   npm test
   ```

## API Endpoints

### Health Check
- **GET** `/health` - Returns server health status

### Books
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books (with optional ?author= filter)
- **GET** `/books/{id}` - Get a single book by ID
- **PUT** `/books/{id}` - Update a book
- **DELETE** `/books/{id}` - Delete a book

## Data Model
- id: number (auto-generated)
- title: string (required)
- author: string (required)
- year: number
- isbn: string

## Implementation Details

This implementation uses Node.js built-in modules only, avoiding external dependencies like SQLite due to compilation issues in the environment.

The API stores data in memory and will be lost when the server restarts. This is sufficient for demonstration purposes.

## Testing

The test suite validates:
1. Health check endpoint
2. Book creation with proper validation
3. Listing all books
4. Getting a book by ID
5. Updating a book
6. Deleting a book
7. Input validation
8. Filtering books by author

To run the tests:
```bash
npm test
```