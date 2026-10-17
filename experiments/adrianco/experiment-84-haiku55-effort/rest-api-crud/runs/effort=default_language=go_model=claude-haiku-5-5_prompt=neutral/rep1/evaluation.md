# Evaluation: effort=default language=go model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=default, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 test functions, all passing / 0 failed / 0 skipped (10 effective) — `test_coverage=0.74`, `defect_rate=1.0` from scores.json
- **Build:** pass (not re-run; `defect_rate=1.0` ⇒ build+test succeeded)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:47 createBook` → `store.go:62 Create`; `TestCreateAndGetBook` |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:62 listBooks` → `store.go:93 List`; `TestListBooksWithAuthorFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:96-99 WHERE author = ? COLLATE NOCASE`; `TestListBooksWithAuthorFilter` (2/3 filtered) |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `handlers.go:71 getBook`, 404 at `:79`; `TestGetMissingBookReturns404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:89 updateBook` → `store.go:124 Update`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:111 deleteBook` → `store.go:142 Delete`, 204; `TestDeleteBook` |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `store.go:9 modernc.org/sqlite`, schema `store.go:15`; `TestDataPersistsAcrossReopen` |
| R8 | JSON responses + status codes | ✓ implemented | `handlers.go:179 writeJSON`; 201/200/404/400/204/503 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `book.go:41-44 Validate`; `TestValidationErrors` (missing/blank → 400) |
| R10 | GET /health health check | ✓ implemented | `handlers.go:38 health` (pings DB); `TestHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup/Run/env vars/build sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 `func Test...` in `server_test.go`; `test_coverage=0.74 > 0` |

## Build & Test

Not re-run — stored mechanical scores used per skill policy:

```text
scores.json: test_coverage=0.74  defect_rate=1.0  code_quality=1.0
             maintainability=0.908  idiomatic=0.82  token_efficiency=0.026
```

`defect_rate=1.0` ⇒ `go build` + `go test` succeeded; `test_coverage=0.74` is line coverage (> 0, tests executed). No skipped/disabled tests (`grep t.Skip` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .go) | 769 |
| Lines of code (non-test) | ~510 (book/handlers/main/store) |
| Source files | 5 .go (4 non-test) |
| Dependencies (go.sum lines) | 50 |
| Tests total | 10 functions |
| Tests effective | 10 |
| Skip ratio | 0% |
| Line coverage | 74% |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are beyond-spec enhancements:

1. [info] Input validation exceeds the spec (year range + ISBN-10/13 checksum) — `book.go:38-85`
2. [info] Hardened HTTP handling + graceful shutdown — `handlers.go:142-160`, `main.go:33-50`

## Reproduce

```bash
cd experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-haiku-5-5_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" server_test.go              # 10 tests
# optional full re-run: go test ./...
```
