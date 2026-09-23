# Book Collection API

A JSON REST API for managing books, written in TypeScript. It uses Node's built-in HTTP server and SQLite module, so there is no separate database server or runtime framework to install. Node.js 22.5 or newer is required.

## Setup and run

```sh
npm install
npm run build
npm start
```

The service listens on port `3000` by default. Set `PORT` to change it and `DATABASE_PATH` to select the SQLite file (defaults to `./books.sqlite`).

## Endpoints

- `GET /health` — returns `{ "status": "ok" }`.
- `POST /books` — create `{ "title", "author", "year?", "isbn?" }`; title and author must be non-empty strings. Returns `201`.
- `GET /books` — list books; optionally filter with `?author=Exact%20Author`.
- `GET /books/:id` — get one book.
- `PUT /books/:id` — replace a book using the same fields as create.
- `DELETE /books/:id` — delete one book.

Missing records return `404`; invalid JSON or invalid input returns `400`. Optional year and ISBN are stored as `null` when omitted.

## Tests

```sh
npm test
```
