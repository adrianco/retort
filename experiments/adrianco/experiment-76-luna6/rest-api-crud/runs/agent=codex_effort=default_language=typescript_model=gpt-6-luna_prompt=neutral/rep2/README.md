# Book Collection API

A JSON REST API for a book collection, built with TypeScript, Node's HTTP server, and SQLite (`node:sqlite`). Data is stored persistently in `books.sqlite` by default.

## Requirements

- Node.js 22.5 or newer (the service uses the built-in `node:sqlite` module)
- npm

## Setup and run

```sh
npm install
npm run build
npm start
```

The server listens on port `3000`. Set `PORT` to change the port and `DATABASE_PATH` to change the SQLite file. For local development with automatic TypeScript execution, use `npm run dev`.

## API

- `GET /health` — service health
- `POST /books` — create `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`; title and author are required, while year and ISBN are optional
- `GET /books` — list all books; optionally filter with `?author=...` (case-insensitive exact match)
- `GET /books/:id` — fetch one book
- `PUT /books/:id` — replace a book using the same body shape as create
- `DELETE /books/:id` — delete a book

Responses are JSON. Creates return `201`, successful reads/updates/deletes return `200`, invalid input returns `400`, missing routes or books return `404`, and unexpected server failures use the platform's HTTP handling.

## Tests

```sh
npm test
```

The tests exercise health, create/read/list filtering, required-field validation, not-found behavior, update, and delete against an in-memory SQLite database.
