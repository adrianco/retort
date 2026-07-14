# Book Collection API

A REST API service for managing a book collection with SQLite database.

## Features

- POST /books - Create a new book
- GET /books - List all books (with optional author filter)
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

## API Endpoints

### Health Check
`GET /health`
Returns server status.

### Create Book
`POST /books`
Request body:
```json
{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```

### List Books
`GET /books`
Optional query parameter:
- `author` - filter books by author name

### Get Book by ID
`GET /books/{id}`

### Update Book
`PUT /books/{id}`
Request body:
```json
{
  "title": "New Title",
  "author": "New Author",
  "year": 2024,
  "isbn": "0987654321"
}
```

### Delete Book
`DELETE /books/{id}`

## Project Structure

- `src/app.js` - Main Express application with routes
- `src/bookService.js` - Database service for book operations
- `src/server.js` - Server entry point

## Implementation Details

The application uses:
- Express.js for the REST API framework
- SQLite for embedded database storage
- Node.js built-in modules for file system operations

## Testing

The project is structured to support unit and integration tests. To run tests:
```bash
npm test
```

## License

MIT