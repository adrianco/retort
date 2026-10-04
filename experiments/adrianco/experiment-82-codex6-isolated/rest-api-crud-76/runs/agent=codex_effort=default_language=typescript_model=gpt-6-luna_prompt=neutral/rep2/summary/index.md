# Architecture Summary

Book Collection REST API in TypeScript on Node's built-in modules — no external runtime dependencies.

## Modules

- `src/books.ts` — `BookStore` data layer over `node:sqlite` (`DatabaseSync`). Creates the `books` table on construction; exposes `list(author?)`, `get(id)`, `create(input)`, `update(id, input)`, `delete(id)`. IDs are `randomUUID()`. `Book` / `BookInput` interfaces define the shape.
- `src/app.ts` — `createApp(db?)` builds a `node:http` server with a hand-rolled router. Helpers: `send()` (JSON + status), `readJson()` (streamed body parse), `validate()` (title/author required, year integer-or-null, isbn string-or-null). Routes: `GET /health`, `GET /books` (+`?author=`), `POST /books`, `GET|PUT|DELETE /books/:id` via regex match.
- `src/server.ts` — entrypoint; `createApp()` on `PORT` (default 3000).
- `test/api.test.ts` — `node:test` integration tests against an in-memory SQLite app on an ephemeral port.

## Flow

HTTP request → `createApp` router dispatch → `BookStore` method → SQLite → JSON response. Dependency injection of the `DatabaseSync` handle into `createApp`/`BookStore` is what lets tests run against `:memory:`.

## Notes

- Clean separation of persistence (`books.ts`) from transport (`app.ts`); testable by construction.
- Zero third-party runtime deps — relies on Node ≥22.5 `node:sqlite`.
