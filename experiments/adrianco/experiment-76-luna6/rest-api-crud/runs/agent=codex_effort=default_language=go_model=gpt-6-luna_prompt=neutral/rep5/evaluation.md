# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, effort=default, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=0.664` in scores.json (build+tests ran; 66.4% coverage)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handler.go:41` POST branch → `books.go:54 create`, 201 |
| R2 | GET /books lists all | ✓ implemented | `handler.go:34` → `books.go:20 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `books.go:23` `WHERE author = ? COLLATE NOCASE`; tested `handler_test.go:59` |
| R4 | GET /books/{id} single | ✓ implemented | `handler.go:69` → `books.go:44 get`; 404 via `writeStoreError` |
| R5 | PUT /books/{id} update | ✓ implemented | `handler.go:76` → `books.go:63 update`; 404 on 0 rows |
| R6 | DELETE /books/{id} delete | ✓ implemented | `handler.go:92` → `books.go:79 delete`; 204 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:30` `sql.Open("sqlite", ...)`, `modernc.org/sqlite`, CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `handler.go:133 writeJSON`; 201/200/204/400/404/405 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `books.go:94 validateBook`; tested `handler_test.go:75` |
| R10 | GET /health | ✓ implemented | `handler.go:24 health`; tested `handler_test.go:81` |
| R11 | README with setup/run | ✓ implemented | `README.md` — run, endpoints, tests sections |
| R12 | ≥ 3 tests | ✓ implemented | 3 `Test*` functions; `test_coverage=0.664` (>0) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: test_coverage=0.664, code_quality=1.0, defect_rate=1.0,
             maintainability=0.795, idiomatic=0.83
```

`test_coverage=0.664` ⇒ `go test ./...` built and ran; all 3 tests pass at 66.4%
statement coverage. `defect_rate=1.0` confirms build+test success. No skipped
tests (`grep t.Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 377 (Go) |
| Files (excl. `_*` logs/meta) | 6 source + README + go.mod/go.sum |
| Dependencies (go.sum lines) | 50 |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Statement coverage | 66.4% |

## Findings

None. All requirements implemented, tests pass, no skipped/disabled tests, no
build or lint failures. `findings.jsonl` is empty (penalty_score = 1.0).

## Reproduce

```bash
cd runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep5
cat scores.json                        # mechanical scores (no re-run)
grep -rEn "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l *.go                             # LOC
# full verification (optional): go test ./...
```
