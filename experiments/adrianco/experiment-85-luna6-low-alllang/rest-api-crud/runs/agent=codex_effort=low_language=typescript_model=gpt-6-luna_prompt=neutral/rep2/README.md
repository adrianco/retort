# Book Collection API

A TypeScript REST API backed by Node's built-in SQLite module. It provides CRUD operations for books and an author filter.

## Setup

Requirements: Node.js 22.13 or newer and npm.

```sh
npm install
```

## Run

```sh
npm run build
npm start
```

The service listens on port `3000` by default and creates `books.sqlite` in the current directory. Set `PORT` to change the port or `DATABASE_PATH` to choose another SQLite file (use `:memory:` for an in-memory database).

## API

- `GET /health` — health status
- `POST /books` — create a book (`title`, `author` required; `year` and `isbn` optional)
- `GET /books` — list books; `?author=...` filters by partial, case-insensitive SQLite match
- `GET /books/:id` — get one book
- `PUT /books/:id` — replace a book's fields
- `DELETE /books/:id` — delete a book

Responses are JSON. Invalid input returns `400`, missing books return `404`, successful creation returns `201`, and successful deletion returns `204`.

## Tests

```sh
npm test
```

Node's built-in `node:sqlite` module is experimental in some Node releases and may print an experimental warning.
