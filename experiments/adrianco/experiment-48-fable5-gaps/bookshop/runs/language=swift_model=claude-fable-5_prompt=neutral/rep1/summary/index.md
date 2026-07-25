# Codebase Summary — book-api (Swift / Hummingbird 2 / SQLite)

A small, well-layered REST service for a book collection. SwiftPM package with
three targets: `App` (library), `Server` (executable), `AppTests` (tests).

## Modules

| File | Responsibility |
|------|----------------|
| `Sources/App/Models.swift` | `Book` (response model), `BookInput` (request body + `validated()` guard), `HealthResponse`. |
| `Sources/App/BookRepository.swift` | `actor BookRepository` — SQLite3-backed store. CRUD + `list(author:)` filter + `ping()`. Serializes the single connection via an actor; uses prepared statements with bound params (SQL-injection safe) and `SQLITE_TRANSIENT`. |
| `Sources/App/BookController.swift` | Routes for `/books`: create/list/get/update/delete. Maps repository results to HTTP status codes (201/200/404/400/204). |
| `Sources/App/Application+build.swift` | `buildApplication(databasePath:host:port:)` wires the router, registers `GET /health` and the books group. Takes `:memory:` for tests. |
| `Sources/Server/Server.swift` | `@main` entry; reads `HOST`/`PORT`/`DB_PATH` env vars, runs the service. |
| `Tests/AppTests/BookAPITests.swift` | 7 `@Test` cases exercising every route via the in-memory router test client. |

## Request flow

`Server.main` → `buildApplication` → `Router` (`/health`, `/books/*`) →
`BookController` handler → `BookRepository` (actor) → SQLite. JSON in/out via
Codable; validation errors and missing rows surface as `HTTPError` with the
right status.

## Design notes

- Clean separation of model / persistence / routing / composition.
- Persistence is real SQLite (system `SQLite3` C library — no extra package dep).
- Actor isolation gives thread-safe DB access with a single connection.
- Case-insensitive author filter (`COLLATE NOCASE`).
- Tests cover happy paths plus 404 (unknown id), 400 (bad id, missing/blank
  fields, malformed JSON), and idempotent delete.
