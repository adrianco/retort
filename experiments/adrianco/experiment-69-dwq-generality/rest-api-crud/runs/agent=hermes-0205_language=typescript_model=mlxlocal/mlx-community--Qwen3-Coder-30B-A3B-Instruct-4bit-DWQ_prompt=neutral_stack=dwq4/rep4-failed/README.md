# Book API REST Service

A REST API service for managing a book collection with SQLite database storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Requirements Met

✅ POST /books — Create a new book (title, author, year, isbn)  
✅ GET /books — List all books (support ?author= filter)  
✅ GET /books/{id} — Get a single book by ID  
✅ PUT /books/{id} — Update a book  
✅ DELETE /books/{id} — Delete a book  
✅ Use SQLite for data storage  
✅ Return JSON responses with appropriate HTTP status codes  
✅ Include input validation (title and author are required)  
✅ Include a health check endpoint: GET /health  

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

## Development

To run in development mode:
```bash
npm run dev
```

## Database

The application uses SQLite for data storage. The database file `books.db` is created automatically in the project root directory.

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
curl http://localhost:3000/books?author=F. Scott Fitzgerald
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```