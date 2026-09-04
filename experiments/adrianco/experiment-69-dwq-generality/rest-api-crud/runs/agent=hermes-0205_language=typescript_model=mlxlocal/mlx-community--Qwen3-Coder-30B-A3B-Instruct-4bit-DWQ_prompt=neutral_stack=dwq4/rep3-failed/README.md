# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, Read, Update, and Delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Endpoints

### Health Check
`GET /health`
Returns server health status.

### Create Book
`POST /books`
Create a new book with title, author, year, and isbn.

### List Books
`GET /books`
List all books. Optional `author` query parameter to filter by author.

### Get Book by ID
`GET /books/{id}`
Get a single book by its ID.

### Update Book
`PUT /books/{id}`
Update a book by ID.

### Delete Book
`DELETE /books/{id}`
Delete a book by ID.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the application:
   ```bash
   npm start
   ```

3. The API will be available at `http://localhost:3000`

## Development

1. Install development dependencies:
   ```bash
   npm install --save-dev
   ```

2. Run in development mode with nodemon:
   ```bash
   npm run dev
   ```

## Testing

Run tests:
```bash
npm test
```

## Database

The application uses an in-memory SQLite database for simplicity. In a production environment, you would want to use a persistent database file.

## Requirements

- Node.js (v14 or higher)
- npm