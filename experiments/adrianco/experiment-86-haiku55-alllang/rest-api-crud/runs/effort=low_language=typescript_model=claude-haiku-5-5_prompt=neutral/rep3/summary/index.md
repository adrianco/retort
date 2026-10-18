# Architecture Summary

`book-api` — a dependency-free TypeScript REST service on Node's built-in `http`
and `node:sqlite` modules. Four source modules with clean separation:

| Module | Role |
|--------|------|
| `src/db.ts` | `BookRepository` — SQLite persistence (`node:sqlite` `DatabaseSync`). CRUD + `ping`/`close`. Table auto-created, WAL journal. |
| `src/validation.ts` | `validateBook` — pure validator returning a discriminated `ValidationResult`. Requires non-empty `title`/`author`; optional integer `year`, string `isbn`. |
| `src/app.ts` | `createApp(repo)` — HTTP router over `node:http`. Dispatches `/health`, `/books`, `/books/{id}`; central error handling via `HttpError`, body-size cap, JSON helper. |
| `src/server.ts` | Entry point — wires repo + app, binds `PORT`, ensures DB dir, graceful SIGINT/SIGTERM shutdown. |

Test: `test/books.test.ts` spins the real server on an ephemeral port against an
in-memory DB and drives it over `fetch` — integration-level coverage of health,
full CRUD, filtering, validation, malformed JSON, and routing/method errors.

Flow: `server.ts` → `createApp` → `route()` → `BookRepository` → SQLite.
Validation sits between the router and the repository on writes.

_(run-summary skill not available in this session; this is a hand summary.)_
