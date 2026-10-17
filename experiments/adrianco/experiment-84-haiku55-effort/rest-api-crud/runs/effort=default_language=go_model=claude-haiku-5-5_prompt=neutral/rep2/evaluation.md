# Evaluation: effort=default language=go model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=default, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 test functions passed / 0 failed / 0 skipped (14 effective; coverage 78.6%)
- **Build:** pass (defect_rate=1.0 from retort.db / scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

Scores read from `scores.json` (no re-run): test_coverage=0.786, defect_rate=1.0 (build+test
succeeded), code_quality=1.0, maintainability=0.887, idiomatic=0.85, token_efficiency=0.033.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:48 createBook` → `store.go:70 Create` (INSERT RETURNING id); TestBookLifecycle |
| R2 | GET /books lists all | ✓ implemented | `server.go:62 listBooks` → `store.go:99 List`; TestListBooksWithAuthorFilter |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:103` WHERE author = ? COLLATE NOCASE; TestListBooksWithAuthorFilter, TestStoreListFiltersByAuthor |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `server.go:71 getBook`; `store.go:87` ErrNotFound → 404 (writeStoreError); TestMissingOrInvalidIDs |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:84 updateBook` → `store.go:130 Update`; TestBookLifecycle, TestUpdateBookValidation |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:101 deleteBook` → `store.go:149 Delete` (204); TestBookLifecycle |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:9` modernc.org/sqlite, `store.go:40 migrate`; TestStorePersistsAcrossReopen |
| R8 | JSON responses + status codes | ✓ implemented | `server.go:173 writeJSON`; 201/200/204/400/404/405/503 across handlers; TestRoutingErrorsAreJSON |
| R9 | Validation: title & author required | ✓ implemented | `book.go:36 Validate`; TestCreateBookValidation, TestBookInputValidate |
| R10 | GET /health | ✓ implemented | `server.go:39 health` pings DB; TestHealth |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, flags, API table, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 14 test functions across 3 files; test_coverage=0.786 (>0) |

No missing or partial requirements. Enhancements beyond spec (E1–E4 in findings) include ISBN
check-digit validation, bounded/strict JSON decoding, JSON-rewritten routing errors, and graceful
shutdown.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: defect_rate=1.0  => build + tests succeeded
             test_coverage=0.786 => tests executed, 78.6% coverage
             code_quality=1.0
go test ./...  (as documented in README) — 14 test functions, 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-blank) | 478 |
| Lines of code (tests, non-blank) | 420 |
| Files (excl. .git) | 18 (7 source/test .go + go.mod/go.sum + README + TASK/stack/meta/logs) |
| Dependencies (go.sum entries) | 50 (1 direct: modernc.org/sqlite) |
| Tests total | 14 functions (0 skipped) |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all informational:

1. [info] E1 — ISBN-10/13 check-digit validation beyond spec
2. [info] E2 — Hardened JSON request handling (1 MiB cap, DisallowUnknownFields, single-object)
3. [info] E3 — JSON-consistent 404/405 and graceful shutdown
4. [info] E4 — Case-insensitive author filter with index and persistence test
5. [info] N1 — README "Go 1.22 or newer" vs go.mod "go 1.26.6" (1.22 is the correct minimum; informational)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rhE "^func Test" *_test.go | wc -l          # 14 test functions
# Optional full verification (not required; scores already stored):
go test ./...
```
