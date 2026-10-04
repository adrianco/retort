# Books API

A small TypeScript REST API backed by SQLite, using Node's built-in HTTP and SQLite modules.

## Requirements

- Node.js 22 or later
- npm

## Setup and run

```sh
npm install
npm run build
npm start
```

The server listens on port `3000`. Set `PORT` to change the port and `DATABASE_PATH` to change the SQLite database file (defaults to `./books.sqlite`). For development, run `npm run dev`.

## Endpoints

- `GET /health`
- `POST /books` with JSON `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` (optional exact `?author=` filter)
- `GET /books/:id`
- `PUT /books/:id` with the same fields as create
- `DELETE /books/:id`

Title and author are required. Year and ISBN are optional. Successful creation returns `201`, deletion returns `204`, invalid input returns `400`, and missing books return `404`.

## Tests

```sh
npm test
```
