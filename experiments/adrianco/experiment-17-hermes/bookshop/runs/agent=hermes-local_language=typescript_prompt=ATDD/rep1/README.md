# Book API

A REST API for managing a book collection.

## Features
- Create books (POST /books)
- List all books (GET /books)
- Get a single book by ID (GET /books/{id})
- Update books (PUT /books/{id})
- Delete books (DELETE /books/{id})
- Health check endpoint (GET /health)
- Filtering by author (GET /books?author=authorName)

## Requirements
- Node.js
- npm

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
GET /health
Returns: { "status": "OK" }

### Create Book
POST /books
Request body:
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "integer (optional)",
  "isbn": "string (optional)"
}

Response: Created book object with status 201

### List Books
GET /books
Optional query parameter: author (filter by author name)
Response: Array of book objects

### Get Book by ID
GET /books/{id}
Response: Book object with status 200 or 404 if not found

### Update Book
PUT /books/{id}
Request body: Same as create
Response: Updated book object with status 200 or 404 if not found

### Delete Book
DELETE /books/{id}
Response: Status 204 if successful or 404 if not found
