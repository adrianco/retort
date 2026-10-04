# Book Collection API

A small JSON REST API backed by SQLite. Requires Node.js 22.5 or newer (uses the built-in `node:sqlite` module).

## Setup and run

```sh
npm install
npm run build
npm start
```

The service listens on port 3000 by default; set `PORT` to change it. The SQLite database is stored in `books.db` in the current directory. For development, `npm run dev` runs the TypeScript source directly.

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book with `title` and `author` (required), and optional `year` and `isbn`
- `GET /books` — list books; use `?author=Name` to filter by exact author
- `GET /books/:id` — retrieve a book
- `PUT /books/:id` — replace a book's fields (title and author required)
- `DELETE /books/:id` — delete a book

Responses use JSON. Invalid input returns `400`; missing books return `404`; successful creation returns `201`, deletion returns `204`.

## Tests

```sh
npm test
```
