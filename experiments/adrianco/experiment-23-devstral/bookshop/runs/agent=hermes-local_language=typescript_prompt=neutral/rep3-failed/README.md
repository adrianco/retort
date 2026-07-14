# Book API

A REST API service for managing a book collection.

## Setup

1. Install Node.js (v14 or higher)
2. Install dependencies:
   ```
   npm install
   ```

## Run the application

```
npm run start
```

The API will be available at `http://localhost:3000`.

## API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/:id` - Get a single book by ID
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book
- `GET /health` - Health check endpoint

## Run tests

```
npm test
```

## Database

The application uses SQLite to store book data. The database file is created in the project root directory as `books.db`.

## Sample Requests

### Create a book

```
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'
```

### List books

```
curl http://localhost:3000/books
```

### Filter books by author

```
curl "http://localhost:3000/books?author=F. Scott Fitzgerald"
```

### Get a book by ID

```
curl http://localhost:3000/books/1
```

### Update a book

```
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'
```

### Delete a book

```
curl -X DELETE http://localhost:3000/books/1
```
