# Evaluation: bookshop-256k · agent=qwen3-coder-local language=go prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=qwen3-coder-local, framework=unknown, prompt=neutral
- **Status:** failed (server panics on startup — `http: multiple registrations for /books`; the built binary does not run as a service)
- **Requirements:** 8/12 implemented, 4 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — `go build` succeeds, binary present (test_coverage=0.552, defect_rate=1.0 from scores.json). **Runtime: fails** (startup panic, confirmed by executing `./bookapi`).
- **Lint:** pass — code_quality=0.9556 from scores.json; idiomatic=0.58
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (1 critical, 3 high, 2 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `handleCreateBook` correct+tested (main.go:187) but route panics/shadowed by GET on `/books` (main.go:295-297) — unreachable |
| R2 | GET /books lists all | ✓ implemented | `handleGetBooks`/`GetAllBooks` (main.go:146,75), tested (main_test.go:102) — but not servable due to panic |
| R3 | GET /books ?author= filter | ✓ implemented | SQL `LIKE` filter (main.go:82), tested (main_test.go:123) |
| R4 | GET /books/{id} single book | ✓ implemented | `GetBook` + `sql.ErrNoRows`→404 (main.go:65,176), tested (main_test.go:147) |
| R5 | PUT /books/{id} updates | ~ partial | shadowed/unreachable (main.go:296) AND 404 branch dead — `db.Exec` never returns ErrNoRows (main.go:107,248) |
| R6 | DELETE /books/{id} deletes | ~ partial | shadowed/unreachable (main.go:296) AND 404 branch dead (main.go:117,273) |
| R7 | SQLite / embedded DB | ✓ implemented | `mattn/go-sqlite3`, real table + SQL (main.go:13,35) |
| R8 | JSON responses + status codes | ~ partial | success paths JSON via `writeJSON`; all error paths use `http.Error` → text/plain (main.go:134,170,177,...) |
| R9 | Validate title+author required | ✓ implemented | 400 on empty title/author (main.go:200-207), tested (main_test.go:83) |
| R10 | GET /health | ✓ implemented | `handleHealth`+`db.Ping` (main.go:132,122), tested (main_test.go:24) — not servable due to panic |
| R11 | README with setup/run | ✓ implemented | README.md documents setup, run, endpoints, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 subtests under TestBookAPI, test_coverage=0.552 |

**Overarching defect:** the startup panic (finding `runtime-panic`) makes every endpoint (R1–R6, R10) non-functional when the program is actually run; R2/R3/R4/R10 are marked implemented at the handler level (logic correct and unit-tested) but would not be reachable until routing is fixed.

## Build & Test

```text
go build            # succeeds — binary `bookapi` produced (11.9 MB)
go test             # passes — 8 subtests, test_coverage=0.552, defect_rate=1.0 (from scores.json)
```

```text
PORT=8099 ./bookapi   # RUNTIME FAILURE
panic: http: multiple registrations for /books
    net/http.HandleFunc(...)
    main.main()  main.go:297
```

Tests pass but never exercise the HTTP mux — they invoke handler methods directly (`store.handleCreateBook(w, req)`), so the routing panic and shadowed write-routes escaped the test suite.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 599 (main.go 308, main_test.go 291) |
| Files (source, excl. artifacts) | 5 (main.go, main_test.go, go.mod, go.sum, README.md) |
| Dependencies (direct) | 1 (github.com/mattn/go-sqlite3) |
| Tests total | 8 subtests |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build | pass; runtime panic |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Server panics on startup: duplicate route registrations (`/books` ×2, `/books/` ×3) — binary crashes on launch (main.go:295-299)
2. [high] POST /books unreachable — create route shadowed by GET + panic (R1)
3. [high] PUT /books/{id} unreachable and 404-on-missing branch is dead (R5)
4. [high] DELETE /books/{id} unreachable and 404-on-missing branch is dead (R6)
5. [medium] Error responses are plain text, not JSON (R8)

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=go_prompt=neutral/rep1
cat scores.json                        # stored build/test/lint scores (no re-run)
grep -n "http.HandleFunc" main.go      # see duplicate /books and /books/ registrations
cp bookapi /tmp/ && (cd /tmp && PORT=8099 ./bookapi)   # observe startup panic
grep -rE "t\.Skip\(" . --include="*.go" | wc -l        # 0 skips
```
