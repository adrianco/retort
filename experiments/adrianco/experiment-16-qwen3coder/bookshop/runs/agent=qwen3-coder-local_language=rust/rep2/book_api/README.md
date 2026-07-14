# Book API

A simple REST API for managing books with a SQLite database backend.

## Features

- Create, read, update, and delete books
- Search books by author
- Health check endpoint
- SQLite database storage

## Endpoints

### Health Check
- `GET /health` - Check if the server is running

### Books
- `POST /books` - Create a new book
- `GET /books` - Get all books (optional author filter)
- `GET /books/:id` - Get a specific book
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book

## API Usage

### Create a Book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Get All Books
```bash
curl http://localhost:3000/books
```

### Get Books by Author
```bash
curl http://localhost:3000/books?author=Fitzgerald
```

### Get a Specific Book
```bash
curl http://localhost:3000/books/{id}
```

### Update a Book
```bash
curl -X PUT http://localhost:3000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Revised Edition",
    "year": 1926
  }'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:3000/books/{id}
```

## Running the Application

1. Make sure you have Rust installed
2. Run `cargo run` to start the server
3. The server will run on `http://localhost:3000`

## Database

The application uses SQLite and stores data in `data/books.db` directory.