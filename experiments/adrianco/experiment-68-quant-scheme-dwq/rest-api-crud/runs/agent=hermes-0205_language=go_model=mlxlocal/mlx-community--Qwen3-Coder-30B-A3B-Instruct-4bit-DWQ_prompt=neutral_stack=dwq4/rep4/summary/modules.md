# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | HTTP server, SQLite init, all CRUD route handlers | `main()`, `initDB()`, `healthHandler`, `booksHandler`, `createBookHandler`, `getBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler`, `Book` |
| `main_test.go` | Handler-level integration tests against a real on-disk SQLite file | 7 test functions, `setupTestDB()` |
| `go.mod` / `go.sum` | Module definition and dependency pins (`mattn/go-sqlite3`, `stretchr/testify`) | module `book-api`, go 1.21 |
| `README.md` | Setup, run, test and curl usage instructions | — |
| `SOLUTION_SUMMARY.md` | Agent-authored narrative of the implementation | — |

Generated/harness files excluded: `_hermes_session.jsonl`, `_agent_*.log`, `_judge/`, `scores.json`, `stack.json`, `_meta.json`, `_effective_stack.json`, `.hermes_usage.json`, `.idiomatic_cache.json`, `TASK.md`, `FEEDBACK.md`, `REQUIREMENTS.json`.
