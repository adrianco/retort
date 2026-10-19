# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, timestamp}` | `index.ts` inline |
| POST | /books | `201 Book` / `400` / `409` | `routes.ts` POST /books |
| GET | /books | `200 [Book]` (optional `?author=`) | `routes.ts` GET /books |
| GET | /books/:id | `200 Book` / `404` | `routes.ts` GET /books/:id |
| PUT | /books/:id | `200 Book` / `400` / `404` / `409` | `routes.ts` PUT /books/:id |
| DELETE | /books/:id | `204` / `404` | `routes.ts` DELETE /books/:id |

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER NOT NULL), isbn (TEXT NOT NULL UNIQUE).

## Library API

Exported helpers: `getDb(customPath?)`, `resetDb()`, `validateBook()`, `validatePartialBook()`, `handleError()`, `parseBody()`.
