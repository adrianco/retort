# Book API

A REST API service for managing a book collection.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Node.js (v14 or higher)
- npm

## Setup

1. Clone the repository
2. Install dependencies:

```bash
npm install
```

3. Start the server:

```bash
npm start
```

Or for development with auto-restart:

```bash
npm run dev
```

## API Endpoints

### Health Check
```
GET /health
```
Returns server status.

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "123-456-789"
}
```

### List Books
```
GET /books
GET /books?author=Author+Name
```

### Get Book by ID
```
GET /books/{id}
```

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "123-456-790"
}
```

### Delete Book
```
DELETE /books/{id}
```

## Testing

Run tests with:

```bash
npm test
```

## Database

The application uses SQLite for data persistence. The database file `books.db` is created in the project root directory.

## Validation

- Title and author are required fields
- ISBN must be unique
- Appropriate HTTP status codes are returned for all operations

## Implementation Details

The implementation follows a clean architecture pattern:
- Express.js for REST API framework
- SQLite for embedded database storage
- Proper HTTP status codes (200, 201, 400, 404, 500)
- Input validation for required fields
- Error handling with appropriate responses
- JSON responses for all endpoints

The server handles all CRUD operations with proper validation and database interaction.