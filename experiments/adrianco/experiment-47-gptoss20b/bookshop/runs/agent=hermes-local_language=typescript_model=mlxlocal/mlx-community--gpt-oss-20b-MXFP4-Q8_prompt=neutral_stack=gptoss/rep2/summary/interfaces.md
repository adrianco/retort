# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) \| `{errors}` (400) | `index.ts:32` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `index.ts:50` |
| GET | /books/:id | `Book` (200) \| 404 | `index.ts:66` |
| PUT | /books/:id | `Book` (200) \| 404 \| `{errors}` (400) | `index.ts:76` |
| DELETE | /books/:id | 204 \| 404 | `index.ts:96` |
| GET | /health | `{status:"ok"}` (200) | `index.ts:109` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT). Stored in an in-memory SQLite database (`:memory:`).
