# Book API

A REST API for managing a book collection with CRUD operations, SQLite database storage, and proper HTTP status codes.

## Features

- Create, Read, Update, Delete books
- SQLite database storage
- Input validation
- Proper HTTP status codes
- Health check endpoint

## API Endpoints

### Health Check
`GET /health`

Returns the health status of the API.

### Get All Books
`GET /books`

Optional query parameter `author` to filter by author.

### Get Book by ID
`GET /books/:id`

### Create Book
`POST /books`

Request body should contain:
- `title` (required)
- `author` (required)
- `year` (optional)
- `isbn` (optional)

### Update Book
`PUT /books/:id`

Request body can contain:
- `title` (optional)
- `author` (optional)
- `year` (optional)
- `isbn` (optional)

### Delete Book
`DELETE /books/:id`

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the server:
   ```bash
   npm start
   ```

3. For development with auto-restart:
   ```bash
   npm run dev
   ```

## Database

The application uses SQLite with a `books.db` file for storage. The database is automatically created with the following schema:

```sql
CREATE TABLE books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT UNIQUE
);
```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 404: Not Found
- 409: Conflict (duplicate ISBN)
- 500: Internal Server Error

## Testing

To run the tests:
```bash
npm test
```