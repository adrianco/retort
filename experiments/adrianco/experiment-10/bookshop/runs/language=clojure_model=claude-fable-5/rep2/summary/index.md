# Architecture Summary: Bookshop API (Clojure)

## Modules

| Module | File | LOC | Purpose |
|--------|------|-----|---------|
| core | `src/bookapi/core.clj` | 14 | Entry point — starts Jetty server, initializes SQLite datasource |
| handler | `src/bookapi/handler.clj` | 93 | HTTP routing (Compojure), JSON serialization, input validation |
| db | `src/bookapi/db.clj` | 42 | Data access layer — CRUD via next.jdbc against SQLite |
| handler_test | `test/bookapi/handler_test.clj` | 119 | Integration tests using ring-mock against temp SQLite DB |

## Stack

- **Language:** Clojure 1.11.3
- **Web framework:** Ring 1.12.2 + Compojure 1.7.1
- **JSON:** Cheshire 5.13.0
- **Database:** SQLite via next.jdbc 1.3.939 + sqlite-jdbc 3.46.1.0
- **Server:** Jetty (ring-jetty-adapter)
- **Testing:** clojure.test + cognitect test-runner + ring-mock

## Data Flow

```
HTTP Request
  → Ring (wrap-params middleware)
    → Compojure route matching (handler.clj)
      → JSON parse + validation (handler.clj)
        → Database operation (db.clj via next.jdbc)
          → SQLite
        ← Result map
      ← JSON response
    ← Ring response map
  ← HTTP Response
```

## Key Design Decisions

- **Embedded SQLite** — no external database server needed; datasource path configurable via `DB_PATH` env var
- **Full validation** — title and author required; year must be integer; isbn must be string; malformed JSON rejected
- **Test isolation** — each test creates a temporary SQLite file, deleted after the test via fixture
- **Clean separation** — handler (HTTP + validation), db (persistence), core (bootstrap) in separate namespaces
