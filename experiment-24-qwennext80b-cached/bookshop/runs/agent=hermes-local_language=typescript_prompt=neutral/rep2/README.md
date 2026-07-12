# Book API REST Service

A REST API service for managing a book collection, built with TypeScript and Express.

## Features

- CRUD operations for books (Create, Read, Update, Delete)
- Author-based filtering
- Input validation
- Health check endpoint
- In-memory storage (configurable via environment variable)

## Setup

### Prerequisites

- Node.js (v16 or higher)
- npm

### Installation

```bash
npm install
```

### Build

```bash
npm run build
```

## Running the Server

### Development Mode

```bash
npm run dev
```

The server will start on port 3000 by default.

### Production Mode

```bash
npm run build
npm start
```

### Environment Variables

- `PORT` - Port to run the server on (default: 3000)
- `DB_PATH` - Path to the SQLite database file (default: `:memory:` for in-memory storage)

Example:

```bash
PORT=8080 DB_PATH=./books.db npm start
```

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2023-10-01T12:00:00.000Z"
}
```

### List All Books

```
GET /books
```

Optional query parameter:
- `author` - Filter by author name

Example:
```
GET /books?author=George%20Orwell
```

### Get Single Book

```
GET /books/:id
```

### Create Book

```
POST /books
```

Request body:
```json
{
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

### Update Book

```
PUT /books/:id
```

Request body (all fields are optional):
```json
{
  "title": "Nineteen Eighty-Four",
  "year": 1949
}
```

### Delete Book

```
DELETE /books/:id
```

## Testing

Run tests:

```bash
npm test
```

Run tests with coverage:

```bash
npm run test:coverage
```

Watch mode:

```bash
npm run test:watch
```

## Project Structure

```
src/
├── controllers/
│   └── BookController.ts
├── database/
│   ├── Database.ts
│   └── BookRepository.ts
├── middleware/
│   └── validation.ts
├── models/
│   └── Book.ts
├── routes/
│   └── books.ts
├── utils/
└── app.ts
└── index.ts
tests/
├── unit.test.ts
└── integration.test.ts
```

## License

ISC
