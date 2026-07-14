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

- Node.js v12 or higher
- npm or yarn

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the server:
   ```bash
   npm start
   ```

3. The API will be available at `http://localhost:3000`

## API Endpoints

### Health Check
- `GET /health` - Check if the service is running

### Books Management
- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/:id` - Get a single book by ID
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl http://localhost:3000/books?author=Fitzgerald
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

## Database

The application uses SQLite for data persistence. The database file `books.db` is created automatically in the project root.