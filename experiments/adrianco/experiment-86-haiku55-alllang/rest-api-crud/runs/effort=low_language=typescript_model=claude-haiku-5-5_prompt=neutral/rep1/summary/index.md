# Architecture Summary

A small, dependency-free TypeScript REST API for a book collection, compiled with `tsc` and run on Node's built-in `http` server. No web framework, no runtime dependencies.

## Modules

| File | Responsibility |
|------|----------------|
| `src/book.ts` | Domain types (`Book`, `BookInput`) and `validateBookInput()` — the validation/normalization layer for create (strict) and update (partial). |
| `src/repository.ts` | `BookRepository` — data access over `node:sqlite` (`DatabaseSync`). CRUD + `ping()` for health, author-indexed table, case-insensitive author filter. |
| `src/app.ts` | `createHandler`/`createServer` — routing over the raw `http` request listener, JSON body reader with a 1 MB cap, central error handling (`HttpError`), status-code mapping. |
| `src/server.ts` | Entry point — wires repo + server, reads `PORT`/`DATABASE_PATH`, SIGINT/SIGTERM graceful shutdown. |
| `tests/books.test.ts` | `node:test` suite: validation units + full HTTP integration against an in-memory DB on a random port. |

## Flow

`server.ts` → `createServer(repo)` → `createHandler(repo)` dispatches by `(method, pathname)`:
`/health` → `repo.ping()`; `/books` GET/POST → `findAll`/`create`; `/books/{id}` GET/PUT/DELETE → `findById`/`update`/`delete`. Request bodies pass through `validateBookInput` before reaching the repository. Errors are normalized to JSON `{error, details?}` with appropriate codes (400/404/405/413/500).

## Notable

- Clean three-layer separation (validation / persistence / transport) despite being a "low effort" run.
- Persistence is real SQLite via `node:sqlite` — no external driver.
- Defensive extras beyond spec: request-size limit, malformed-JSON handling, 405 on wrong method, ISBN/year range validation, graceful shutdown.
