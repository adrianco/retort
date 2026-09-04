# Book API REST Service

REST API service for managing a book collection with SQLite database.

## Features

- Create books (POST /books)
- Get all books (GET /books)
- Get a single book by ID (GET /books/:id)
- Update a book (PUT /books/:id)
- Delete a book (DELETE /books/:id)
- Health check endpoint (GET /health)

## Requirements

- Node.js v16+ 
- npm (or yarn)

## Installation

```bash
npm install
```

## Running the Application

```bash
npm run build
npm start
```

## Development

```bash
npm run dev
```

## Testing

```bash
npm test
```

## API Endpoints

### Health Check
GET /health
Response: { "status": "OK" }

### Create Book
POST /books
Request body:
```json
{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "1234567890"
}
```
Response: { "id": 1 }

### Get All Books
GET /books
Response: Array of book objects

### Get Book by ID
GET /books/:id
Response: Book object or 404 error

### Update Book
PUT /books/:id
Request body:
```json
{
  "title": "Updated Book Title",
  "author": "Updated Author Name",
  "year": 2024,
  "isbn": "0987654321"
}
```
Response: { "message": "Book updated successfully" }

### Delete Book
DELETE /books/:id
Response: { "message": "Book deleted successfully" }

## Testing

Tests are written with Jest and run using:
```bash
npm test
```

## Architecture

The application uses:
- Express.js for the web server
- SQLite for data storage
- TypeScript for type safety
- Jest for testing