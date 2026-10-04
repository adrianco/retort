# Book Collection API

A small REST API for managing books, built with TypeScript, Express, and Node's built-in SQLite support.

## Requirements

Node.js 22.5 or newer and npm. Node 22.5 introduced the built-in `node:sqlite` module.

## Setup and run

```sh
npm install
npm run dev
```

The service listens on port 3000 by default. Set `PORT` to change the port and `DATABASE_PATH` to choose the SQLite file (defaults to `books.sqlite` in the working directory).

For a production build, run `npm run build` followed by `npm start`.

## API

- `GET /health` returns `{ "status": "ok" }`.
- `POST /books` accepts `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`. Title and author are required; year and ISBN are optional.
- `GET /books` lists books. Add `?author=Name` to filter by exact author name.
- `GET /books/:id` returns one book.
- `PUT /books/:id` replaces the book fields using the same JSON shape as POST.
- `DELETE /books/:id` removes the book and returns 204.

Responses use JSON. Invalid input returns 400 and requests for missing books return 404.

## Tests

```sh
npm test
```
