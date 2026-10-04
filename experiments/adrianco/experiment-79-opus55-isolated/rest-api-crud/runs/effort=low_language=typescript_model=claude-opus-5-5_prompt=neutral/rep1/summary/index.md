# Architecture Summary — books-api (TypeScript / Express 5 / node:sqlite)

> `run-summary` skill was not invokable in this session; this summary was written by hand.

## Modules

| File | Responsibility |
|------|----------------|
| `src/server.ts` | Entry point. Reads `PORT`/`DB_PATH` env vars, constructs `BookStore`, starts the HTTP listener. |
| `src/app.ts` | `createApp(store)` — builds the Express app and all routes; JSON body parsing, 404 fallback, and a JSON error handler (malformed body → 400). |
| `src/db.ts` | `BookStore` — SQLite persistence via Node's built-in `node:sqlite` `DatabaseSync`. CRUD + case-insensitive author filter. Defines `Book`/`BookInput`. |
| `src/validation.ts` | `validateBook` (title/author required, optional integer year, optional string isbn) and `parseId` (positive-integer id guard). |
| `tests/api.test.ts` | 9 integration tests over an in-memory store using a real ephemeral listener + `fetch`. |

## Interfaces

- HTTP: `GET /health`, `POST /books`, `GET /books` (`?author=`), `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id`.
- `BookStore`: `create`, `list(author?)`, `get(id)`, `update(id, input)`, `delete(id)`, `close()`.
- `validateBook(body) -> {ok:true,value} | {ok:false,errors}`; `parseId(raw) -> number | undefined`.

## Flow

`server.ts` → `createApp(store)` wires routes → each route validates input (`validation.ts`),
delegates persistence to `BookStore` (`db.ts`), and returns JSON with status codes
(201 create, 200 read/update, 204 delete, 400 validation, 404 not-found). The store is
injected, which is what lets tests swap in an in-memory SQLite DB.

## Notable design choices

- Dependency injection of `BookStore` into `createApp` → clean testability.
- Zero native/runtime deps beyond Express: uses Node's built-in `node:sqlite`.
- Full-replacement PUT semantics (same validation as POST), documented in the README.
- Defensive `parseId` rejects non-numeric / overlong ids as 404.
