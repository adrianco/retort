# Book Collection API

A JSON REST API for managing books, built with TypeScript and Node.js's built-in HTTP server and `node:sqlite` module (Node.js 22.5 or newer). No package install or separate database server is needed.

## Setup and run

```sh
npm start
```

The API listens on `http://localhost:3000`. Set `PORT` to change the port and `DATABASE_PATH` to change the SQLite file (defaults to `books.sqlite` in the current directory).

Run the build check and tests:

```sh
npm run build
npm test
```

## Endpoints

- `GET /health` — returns `{ "status": "ok" }`.
- `POST /books` — create `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }`. Title and author are required; year and ISBN are optional.
- `GET /books` — list books; optionally filter with `?author=Frank%20Herbert` (case-insensitive exact match).
- `GET /books/:id` — retrieve a book.
- `PUT /books/:id` — replace a book's fields using the same shape as create.
- `DELETE /books/:id` — delete a book (returns `204`).

Invalid input returns `400`, missing books return `404`, creation returns `201`, and successful reads and updates return `200`. All response bodies are JSON except the empty successful delete response.

## Tests

```sh
npm test
```
