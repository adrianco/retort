# Book Collection API

A small REST API written in TypeScript with Node's HTTP server and built-in SQLite support (`node:sqlite`). Requires Node.js 22.5 or newer.

## Setup

```sh
npm install
npm run build
```

## Run

```sh
npm start
```

The service listens on port 3000 by default. Set `PORT` to change it and `DATABASE_PATH` to choose the SQLite database file (defaults to `books.sqlite`). For development, `npm run dev` runs the TypeScript source directly.

## Endpoints

- `GET /health`
- `POST /books` with JSON `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` (optional exact `?author=...` filter)
- `GET /books/:id`
- `PUT /books/:id` with the same fields as create
- `DELETE /books/:id`

Title and author are required for create and update. Year and ISBN are optional. Errors are returned as JSON with suitable 4xx status codes.

## Tests

```sh
npm test
```
