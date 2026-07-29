# Book Collection API

## Setup

Requires Node.js 20+.

```sh
npm install
npm test
npm run build
```

## Run

```sh
npm start
```

The server listens on port 3000 (override with `PORT`). Books are stored in `data/books.db`; override the database path with `DATABASE_PATH`.

Endpoints: `GET /health`, `POST /books`, `GET /books?author=...`, `GET /books/:id`, `PUT /books/:id`, and `DELETE /books/:id`. Create requests require non-empty `title` and `author`; `year` must be a non-negative integer when supplied.
