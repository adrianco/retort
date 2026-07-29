# Book Collection API

REST API built with TypeScript, Node's built-in HTTP server, and SQLite. It requires Node.js 22.5+ (for the built-in `node:sqlite` module).

## Setup and run

```sh
npm install
npm run build
npm start
```

The server listens on port 3000. Set `PORT` and `DATABASE_PATH` to customize it. The default database is `./books.sqlite`.

## Endpoints

- `GET /health`
- `POST /books` with `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books?author=...`
- `GET /books/:id`
- `PUT /books/:id` (same body as POST)
- `DELETE /books/:id`

Title and author are required. Missing resources return 404, invalid input returns 400, creation returns 201, and successful deletion returns 204.

## Tests

```sh
npm test
```
