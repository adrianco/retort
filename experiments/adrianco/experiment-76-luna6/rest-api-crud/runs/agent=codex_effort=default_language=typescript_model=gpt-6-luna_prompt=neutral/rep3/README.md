# Book Collection API

A small TypeScript REST API for managing books. It uses Node.js' built-in HTTP server and embedded SQLite database (`node:sqlite`), so there are no runtime dependencies.

## Requirements

- Node.js 22.13 or newer (Node 26 is also supported)
- npm

## Setup and run

```sh
npm install
npm run build
npm start
```

The service listens on port `3000` by default. Set `PORT` to change it and `DATABASE_PATH` to choose the SQLite file (default: `./books.sqlite`). For development, run `npm run dev` to start the TypeScript source directly on Node.js 22.6+.

## API

- `GET /health` — health status
- `POST /books` — create `{ "title", "author", "year?", "isbn?" }` (title and author are required)
- `GET /books` — list books; optionally filter by exact author with `?author=...`
- `GET /books/:id` — retrieve a book
- `PUT /books/:id` — replace a book's fields; title and author are required
- `DELETE /books/:id` — delete a book

Successful responses and errors are JSON. Creation returns `201`, deletion returns `204`, invalid input returns `400`, missing books return `404`, and server errors return `500`.

## Tests

```sh
npm test
```

The integration tests use temporary SQLite databases and exercise CRUD, author filtering, validation, missing records, and the health endpoint.
