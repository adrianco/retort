# Architecture Summary

REST book-collection API in TypeScript on Node's built-in HTTP server and the
built-in `node:sqlite` module — no external runtime framework or DB server.

## Modules

- **`src/books.ts`** — persistence + validation.
  - `BookStore` wraps a `DatabaseSync` connection, creates the `books` table on
    construction, and exposes `list(author?)`, `get(id)`, `create(input)`,
    `update(id, input)`, `delete(id)`, `close()`. Prepared statements throughout;
    `list` uses an exact `author = ?` filter.
  - `validateBook(value)` returns `{input}` or `{error}` — enforces object body,
    required non-empty `title`/`author`, optional non-negative integer `year`,
    optional string `isbn`.
  - `Book` / `BookInput` interfaces model the row shape (`year`/`isbn` nullable).

- **`src/server.ts`** — HTTP routing.
  - `createApp(store?)` returns an `http.Server`; dependency-injectable store makes
    it testable. Routes: `GET /health`, `GET /books` (+`?author=`), `POST /books`,
    `GET|PUT|DELETE /books/:id`. `:id` parsed and range-checked
    (`Number.isSafeInteger`, `>= 1`).
  - `readJson` streams the body with a 1 MB cap and JSON-parse guard → 400 on bad
    input. `send` writes JSON with the right status code.
  - `require.main` guard starts the listener (`PORT`, default 3000) with
    SIGINT/SIGTERM graceful shutdown.

## Flow

Request → URL/method dispatch in `createApp` → `validateBook` (writes) →
`BookStore` prepared statement → SQLite → JSON response with status code.

## Test surface

`test/books.test.cjs` — 3 `node:test` cases against the compiled `dist/books.js`,
covering validation, create/list/get with author filter, and update/delete plus
missing-id handling. Tests target the store + validation layer directly; the HTTP
handler layer in `server.ts` is exercised indirectly, not via live requests.
