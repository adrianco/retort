# Book Collection REST API

A REST API service for managing a book collection with in-memory storage.

## Features
- Create books (POST /books)
- List all books (GET /books)
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)
- Input validation (title and author are required)
- Filtering by author

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run the application:
```bash
npm start
```

3. Run tests:
```bash
npm test
```

## API Endpoints

### Health Check
- `GET /health` - Returns service health status

### Books Management
- `POST /books` - Create a new book  
  Request body: `{ "title": "string", "author": "string", "year": "number", "isbn": "string" }`
  Response: Created book object with ID

- `GET /books` - List all books (supports ?author= filter)
  Response: Array of book objects

- `GET /books/{id}` - Get a single book by ID
  Response: Book object

- `PUT /books/{id}` - Update a book
  Request body: `{ "title": "string", "author": "string", "year": "number", "isbn": "string" }`
  Response: Updated book object

- `DELETE /books/{id}` - Delete a book
  Response: Success message

## Requirements
- Node.js 16+
- Express.js for HTTP handling

## Implementation Details
This implementation uses in-memory storage for demonstration purposes. In a production environment, you would replace this with a proper database like SQLite, PostgreSQL, or MongoDB.

## Testing
The API is tested with comprehensive acceptance tests covering:
- Health check endpoint
- Book creation with validation
- Book retrieval by ID
- Book listing with filtering
- Book updates
- Book deletion
- Error handling for invalid operations