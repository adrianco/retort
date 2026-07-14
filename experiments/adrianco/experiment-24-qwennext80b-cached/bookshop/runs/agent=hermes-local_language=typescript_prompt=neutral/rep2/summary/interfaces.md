# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, timestamp}` | `app.ts` inline |
| GET | /books | `[Book]` (optional `?author=` exact-match filter) | `BookController.getAll` |
| GET | /books/:id | `Book \| 404` | `BookController.getById` |
| POST | /books | `Book` (201) / `400` validation | `BookController.create` |
| PUT | /books/:id | `Book` / `400` / `404` | `BookController.update` |
| DELETE | /books/:id | `204` / `404` | `BookController.delete` |

Unhandled errors return `500 {error: 'Internal server error'}` via the app-level error middleware.

## Validation

- Create (`validateBookInput`): `title`, `author`, `isbn` required non-empty strings; `year` required non-negative integer.
- Update (`validateBookUpdate`): all fields optional; if present, same type/non-empty constraints.
- Failures return `400 {error: 'Validation failed', details: [...]}`.

## CLI commands

(none)

## Library API

Exported symbols: `app`, `server`, `BookController`, `BookRepository`/`bookRepository`, `DatabaseManager`/`db`, `validateBookInput`, `validateBookUpdate`, `validateBookCreate`, `validateBookUpdate` (middleware), and the `Book`/`BookInput`/`BookUpdate` types.

## Data schema

In-memory `BookRow[]` array (not SQLite). Fields: `id` (int, auto-increment via max+1), `title` (str), `author` (str), `year` (int), `isbn` (str), `createdAt` (ISO str), `updatedAt` (ISO str). Optionally persisted to a JSON file when `DB_PATH` is set to a path other than `:memory:`.
