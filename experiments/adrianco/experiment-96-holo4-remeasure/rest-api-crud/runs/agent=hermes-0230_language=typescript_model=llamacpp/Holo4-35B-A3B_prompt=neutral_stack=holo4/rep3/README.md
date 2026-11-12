# Book API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/:id` | Get a single book |
| PUT | `/books/:id` | Update a book |
| DELETE | `/books/:id` | Delete a book |

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

The server starts on port 3000 by default.

## Tests

```bash
npm test
```
