# Book API

A small REST API for managing a book collection.

## Features

* CRUD endpoints for books
* SQLite in‑memory database (no external DB required)
* Input validation for `title` and `author`
* Health check endpoint
* Tests written with Jest & Supertest

## Getting started

```bash
# Install dependencies
npm install

# Run the server (development)
pm run dev
# or
# Build and start
npm run build
npm start
```

The server listens on port `3000` (or the value of the `PORT` env variable).

## Running tests

```bash
npm test
```

The test suite covers the health check, CRUD operations, filtering, and error handling.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | /books | Create a new book (JSON body: `title`, `author`, `year?`, `isbn?`) |
| GET    | /books | List all books. Optional query `author` to filter by author |
| GET    | /books/:id | Get a single book by ID |
| PUT    | /books/:id | Update a book (JSON body same as POST) |
| DELETE | /books/:id | Delete a book |
| GET    | /health | Health check – returns `{ status: "ok" }` |

## License

MIT
