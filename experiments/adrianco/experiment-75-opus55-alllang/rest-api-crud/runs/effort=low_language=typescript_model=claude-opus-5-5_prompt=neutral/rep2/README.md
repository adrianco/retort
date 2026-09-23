# Book Collection API

TypeScript REST API using Node's built-in `node:http` and `node:sqlite` (requires Node.js 22.5+; no runtime dependencies).

## Setup & run

```sh
npm install
npm run build
npm start            # http://localhost:3000  (env: PORT, DB_PATH — default books.db)
npm test             # builds and runs integration tests (in-memory DB)
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | list; `?author=` filter (case-insensitive exact match) |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full update, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 or 404 |
