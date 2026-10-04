# Architecture Summary

Standard-library Go HTTP service (no web framework) backed by SQLite via the
pure-Go `modernc.org/sqlite` driver. Four source files, clean separation:

| File | Role |
|------|------|
| `main.go` | Process entry point: config from env (`PORT`, `DB_PATH`), opens the store, wires `http.Server` with sane timeouts, graceful shutdown on SIGINT/SIGTERM. |
| `store.go` | Persistence layer. `Store` wraps `*sql.DB`; schema auto-created; `Book`/`BookInput` models; CRUD methods (`Create`/`List`/`Get`/`Update`/`Delete`) using parameterized queries; `ErrNotFound` sentinel; WAL mode + busy_timeout; URI-escaping of the DB path; `:memory:` handling. |
| `handlers.go` | HTTP layer. `Server` holds the store + logger. Go 1.22+ method-aware `ServeMux` routes (`POST /books`, `GET /books/{id}`, etc.); JSON encode/decode with strict body handling (max-bytes reader, single-object enforcement, typed decode errors); `validateBook` field validation; method-not-allowed + 404 JSON fallbacks; request-logging middleware. |
| `handlers_test.go` | 14 test functions (many table-driven with subtests) exercising every route, validation branch, error path, persistence across reopen, in-memory store, and SQL-injection resistance. |

## Request flow

`main.run` → `NewServer(store, logger)` returns a `logRequests`-wrapped mux →
per-route handler → `readBookInput`/`parseID` validate → `Store` method →
`writeJSON`/`writeError` renders the response with the correct status code.

## Notable properties

- Parameterized SQL throughout; an explicit test asserts the `?author=` filter is
  not injectable.
- PUT is full-replacement semantics (omitted fields cleared) — documented in tests.
- Empty list returns `[]`, not `null`.
- Graceful shutdown with a 10s drain timeout.
