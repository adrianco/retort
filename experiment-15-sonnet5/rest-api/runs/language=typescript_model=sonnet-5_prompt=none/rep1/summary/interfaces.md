# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:'ok'}` | `app.ts:10` |
| POST | /books | `201 Book` \| `400 {errors}` | `app.ts:14` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.ts:29` |
| GET | /books/:id | `200 Book` \| `400` \| `404` | `app.ts:40` |
| PUT | /books/:id | `200 Book` \| `400` \| `404` | `app.ts:52` |
| DELETE | /books/:id | `204` \| `400` \| `404` | `app.ts:83` |

## Library API

- `createApp(db: DatabaseSync): Express` — builds the route table over a DB handle.
- `createDatabase(filename: string): DatabaseSync` — opens SQLite + creates `books` table.
- `validateBookInput(body, {partial?}): ValidationResult` — required/typed field validation.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
