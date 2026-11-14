# Book Collection REST API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/:id` | Get a single book by ID |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

## Book Fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

## Setup and Run

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Start the server
npm start

# Run tests
npm test
```

The server runs on port 3000 by default.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=F. Scott Fitzgerald"

# Get a book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```
