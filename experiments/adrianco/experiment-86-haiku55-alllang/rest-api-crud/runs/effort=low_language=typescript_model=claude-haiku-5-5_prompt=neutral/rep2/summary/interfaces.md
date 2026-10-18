# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.ts` health branch |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.ts` → `BookRepository.list` |
| POST | /books | `201 Book` \| `400` | `app.ts` → `validateBook` + `BookRepository.create` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `app.ts` → `BookRepository.findById` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.ts` → `validateBook` + `BookRepository.update` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `app.ts` → `BookRepository.delete` |

Unknown routes → `404`; unsupported methods on a known path → `405`; oversized body → `413`; malformed/empty JSON → `400`.

## Library API

- `openDatabase(path = ':memory:'): Database` — creates the `books` table + author index.
- `BookRepository` — `create`, `findById`, `list(author?)`, `update`, `delete`.
- `validateBook(body): ValidationResult` — title/author required, year 0–3000 integer, isbn non-empty string.
- `parseId(raw): number | null` — positive safe integer only.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER nullable), `isbn` (TEXT nullable). Index `idx_books_author` on `author`.
