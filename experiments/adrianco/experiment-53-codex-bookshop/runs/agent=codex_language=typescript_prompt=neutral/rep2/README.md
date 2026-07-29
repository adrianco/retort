# Books API

An Express/TypeScript REST API backed by SQLite.

## Setup

Requires Node.js 18 or newer.

```sh
npm install
npm test
npm run build
```

## Run

```sh
npm start
```

The service listens on port `3000` by default. Set `PORT` and/or `DATABASE_PATH` to customize it. The database defaults to `./books.db`.

Endpoints are `GET /health`, and the CRUD routes `POST /books`, `GET /books?author=...`, `GET /books/:id`, `PUT /books/:id`, and `DELETE /books/:id`. Book JSON uses `title` and `author` (required), with optional `year` and `isbn` fields.
