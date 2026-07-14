# Book API

A REST API service for managing a book collection.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Start the server:
   ```
   npm start
   ```

   Or for development with auto-restart:
   ```
   npm run dev
   ```

## Testing

Run tests with:
```
npm test
```

## Database

The application uses SQLite for data storage. The database file `books.db` will be created automatically in the project root.

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1948,"isbn":"978-0-452-28423-4"}'
```

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl http://localhost:3000/books?author=George%20Orwell
```

### Get a single book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1948,"isbn":"978-0-452-28423-4"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```