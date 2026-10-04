# Book Collection API

A small TypeScript REST API backed by SQLite. It requires Node.js 22 or newer (for the built-in `node:sqlite` module) and npm.

## Setup and run

```sh
npm install
npm run build
npm start
```

The server listens on port `3000` by default. Set `PORT` to change it and `DATABASE_PATH` to select the SQLite database file (defaults to `books.db`). For development, run `npm run dev`.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with JSON `{ "title", "author", "year?", "isbn?" }`
- `GET /books?author=...` — list books, optionally filtered by exact author
- `GET /books/:id` — retrieve a book
- `PUT /books/:id` — replace a book's fields using the same JSON shape as create
- `DELETE /books/:id` — delete a book

Invalid JSON or invalid book fields return `400`; missing books return `404`; successful creation returns `201`. All responses are JSON.

## Tests

```sh
npm test
```
