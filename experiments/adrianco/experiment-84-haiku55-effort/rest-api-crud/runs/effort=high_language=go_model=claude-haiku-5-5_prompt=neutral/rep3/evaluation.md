# Evaluation: effort=high language=go model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 test functions, all passing / 0 failed / 0 skipped (16 effective) — `defect_rate=1.0` (build+tests pass), `test_coverage=0.772` (coverage fraction)
- **Build:** pass — from `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:23` `createBook` → `store.go:59` `Create`; test `api_test.go:77` |
| R2 | GET /books lists all books | ✓ implemented | `server.go:24` `listBooks` → `store.go:90` `List`; test `api_test.go:172` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `server.go:60` reads `author`; `store.go:93` `WHERE author = ? COLLATE NOCASE`; test `store_test.go:74` |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `server.go:25` `getBook`; `store.go:79` maps `ErrNoRows`→`ErrNotFound`→404; test `api_test.go:154` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:26` `updateBook` → `store.go:121` `Update`; test `api_test.go:206` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:27` `deleteBook` → `store.go:139` `Delete`; test `api_test.go:237` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:9` `modernc.org/sqlite` (pure-Go), schema `store.go:15` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `server.go:185`; 201/200/404/400/204/503 used across handlers |
| R9 | Validation: title and author required | ✓ implemented | `book.go:51-55` `Validate`; test `api_test.go:103` + `book_test.go:8` |
| R10 | GET /health health-check endpoint | ✓ implemented | `server.go:22` `health` pings DB, returns `{"status":"ok"}`; test `api_test.go:64` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — requirements, `go mod download`, `go run`, build, flags/env table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 16 test functions across 3 files; `test_coverage=0.772 > 0` |

No requirement is partial or missing. No requirement scored on a stub.

## Build & Test

Scores read from `scores.json` (not re-run, per skill Step 2):

```text
defect_rate   = 1.0    => build succeeded AND all tests passed
code_quality  = 1.0    => lint/quality clean
test_coverage = 0.772  => 77.2% statement coverage (tests executed and passed)
idiomatic     = 0.9
maintainability = 0.924
```

No skipped or disabled tests: `grep -E "t\.Skip\(|t\.Skipf\(" *.go` → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, excl. tests) | 551 |
| Lines of code (tests) | 511 |
| Files (excl. .git) | 18 |
| Dependencies (go.sum lines) | 50 (1 direct: `modernc.org/sqlite`) |
| Tests total | 16 functions |
| Tests effective | 16 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (scores from DB/scores.json) |

## Findings

All findings are informational (full list in `findings.jsonl`):

1. [info] ISBN-10/13 checksum validation beyond spec (`book.go:88`)
2. [info] Hardened request decoding — unknown-field rejection + 1 MiB cap (`server.go:164`)
3. [info] Graceful shutdown + configurable addr/db (`cmd/bookapi/main.go`)
4. [info] Coverage 77.2% (not a defect; build+tests pass) — untested startup/shutdown path

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=go_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rhE "^func Test" *_test.go | wc -l          # 16 test functions
# Optional fresh run (toolchain permitting): go test ./...
```
