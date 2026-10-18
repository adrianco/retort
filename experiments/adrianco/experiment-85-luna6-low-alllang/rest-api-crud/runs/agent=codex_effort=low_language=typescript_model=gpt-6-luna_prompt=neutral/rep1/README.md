# Book Collection API

A TypeScript REST API for managing a book collection. Express handles HTTP requests, and Node.js's built-in SQLite API stores books in `books.sqlite` in the current working directory (Node.js 22.13 or newer).

## Setup

Requires Node.js 18 or newer.

```sh
npm install
```

## Run

```sh
npm run dev
```

The service listens on port `3000` by default. Set `PORT` to use a different port. To build and run the compiled version, use `npm run build` followed by `npm start`.

## API

- `GET /health` — health status.
- `POST /books` — create a book. JSON fields: `title` and `author` (required), `year` and `isbn` (optional).
- `GET /books` — list books; optionally filter with `?author=Name`.
- `GET /books/:id` — retrieve a book.
- `PUT /books/:id` — replace a book's fields using the same JSON shape as creation.
- `DELETE /books/:id` — remove a book (returns `204` on success).

Validation errors return `400`, missing books return `404`, and successful creation returns `201`.

## Tests

```sh
npm test
```
