# Books API

A TypeScript REST API for a SQLite-backed book collection.

## Setup

Requires Node.js 20 or newer and npm.

```sh
npm install
```

## Run

```sh
npm run dev
```

The service listens on port `3000`. Set `PORT` to change the port and `DATABASE_PATH` to choose the SQLite database file (defaults to `books.db` in the current directory).

## API

- `GET /health` — health status
- `POST /books` — create `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` — list books; add `?author=Name` to filter by exact author
- `GET /books/:id` — fetch a book
- `PUT /books/:id` — replace the book fields with the same shape as create
- `DELETE /books/:id` — delete a book

Title and author are required. Year and ISBN are optional. Responses use JSON; deletion returns `204 No Content` on success. Invalid input returns `400`, missing books return `404`, and creation returns `201`.

## Build and test

```sh
npm run build
npm test
```
