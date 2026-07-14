# Book API

A REST API service for managing a book collection.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Node.js (v12 or higher)
- npm

## Setup

1. Clone or download this repository
2. Install dependencies:
   ```bash
   npm install
   ```

## Run

Start the server:
```bash
npm start
```

The server will run on `http://localhost:3000`

## API Endpoints

### Health Check
- **GET** `/health` - Check if the service is running

### Books
- **POST** `/books` - Create a new book
  - Request body: `{ "title": "string", "author": "string", "year": number, "isbn": "string" }`
  - Returns: Created book object with ID
- **GET** `/books` - List all books
  - Query parameters: `?author=author_name` (optional filter)
  - Returns: Array of book objects
- **GET** `/books/:id` - Get a single book by ID
  - Returns: Book object
- **PUT** `/books/:id` - Update a book
  - Request body: `{ "title": "string", "author": "string", "year": number, "isbn": "string" }`
  - Returns: Updated book object
- **DELETE** `/books/:id` - Delete a book
  - Returns: Success message

## Testing

Run the tests:
```bash
npm test
```

## Implementation Details

- Built with Node.js and Express
- Uses SQLite for data storage (in-memory for simplicity)
- All endpoints return JSON responses with appropriate HTTP status codes
- Input validation for required fields (title and author)
- Unique constraint on ISBN