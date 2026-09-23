# Book Collection API

A small TypeScript REST API backed by SQLite.

## Requirements

Node.js 22.5 or later (uses the built-in `node:sqlite` module).

## Setup and run

```sh
npm install
npm run build
npm start
```

The service listens on port `3000`. Set `PORT` to change it and `DATABASE_PATH` to choose the SQLite file (default: `data/books.sqlite`). For development with automatic TypeScript execution, run `npm run dev`.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with `{ "title", "author", "year", "isbn" }`
- `GET /books` — list books; optionally filter with `?author=...`
- `GET /books/:id` — fetch one book
- `PUT /books/:id` — replace a book's fields
- `DELETE /books/:id` — delete a book

Titles and authors must be non-empty strings. Year must be a non-negative integer; ISBN must be a non-empty string. Responses use JSON; invalid input returns `400`, missing books return `404`, and successful creation returns `201`.

## Tests

```sh
npm test
```
