# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database,uptime,timestamp}` / `503` | `app.ts` health handler (calls `repo.ping()`) |
| GET | /books | `200 [Book]` (optional `?author=` case-insensitive exact filter) / `400` on repeated param | `app.ts` list handler |
| POST | /books | `201 Book` + `Location` header / `400` | `app.ts` create handler |
| GET | /books/:id | `200 Book` / `400` bad id / `404` | `app.ts` get handler |
| PUT | /books/:id | `200 Book` / `400` / `404` | `app.ts` update handler |
| DELETE | /books/:id | `204` / `400` / `404` | `app.ts` delete handler |
| * | (unmatched) | `404 {error:"Not found"}` | fallback middleware |

## Library API

- `createApp(repo: BookRepository): express.Express`
- `BookRepository(path)` — `list({author?})`, `get(id)`, `create(input)`, `update(id,input)`, `delete(id)`, `ping()`, `close()`
- `validateBookInput(body): ValidationResult`, `parseId(raw): number | null`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT), `created_at` (TEXT), `updated_at` (TEXT). Index `idx_books_author` on `author`. WAL journal mode.
