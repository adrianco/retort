# Book API REST Service

A REST API service for managing a book collection using TypeScript, Express, and SQLite.

## Features

- Create books (POST /books)
- List all books (GET /books)
- Filter books by author (GET /books?author={author})
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Node.js (v16 or higher)
- npm or yarn

## Setup

1. Clone or copy this project to your workspace directory

2. Install dependencies:

```bash
npm install
```

3. Build the project:

```bash
npm run build
```

## Running

### Development Mode

```bash
npm run dev
```

The server will start on port 3000 by default.

### Production Mode

```bash
# Build first
npm run build

# Start the server
npm start
```

## Environment Variables

- `PORT` - Port to run the server (default: 3000)
- `DB_PATH` - Path to the SQLite database file (default: ./books.db)

## API Endpoints

### Health Check
```
GET /health
```
Response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### List All Books
```
GET /books
GET /books?author=Author%20Name
```

### Get Book by ID
```
GET /books/{id}
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "978-1234567890"
}
```
Response: 201 Created

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2025,
  "isbn": "978-0987654321"
}
```
Response: 200 OK

### Delete Book
```
DELETE /books/{id}
```
Response: 204 No Content

## Testing

Run tests with Jest:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

## Project Structure

```
src/
├── controllers/
│   └── bookController.ts
├── models/
│   └── BookModel.ts
├── routes/
│   └── bookRoutes.ts
├── middleware/
│   └── validation.ts
├── types/
│   └── book.d.ts
├── __tests__/
│   ├── bookAPI.test.ts
│   └── healthCheck.test.ts
└── server.ts
```

## License

ISC
