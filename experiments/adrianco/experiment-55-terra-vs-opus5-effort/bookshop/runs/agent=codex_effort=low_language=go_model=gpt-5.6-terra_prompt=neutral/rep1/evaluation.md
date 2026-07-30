# Evaluation: agent=codex effort=low language=go model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** single-file Go net/http service (`main.go`) over SQLite; summary skill not invoked
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:94 createBook`, INSERT at :99 |
| R2 | GET /books lists all | ✓ implemented | `main.go:64 listBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:67-70`; test `TestListFiltersByAuthor` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:108 getBook`/`findBook`, 404 at :164 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:116 updateBook`, 404 on 0 rows :131 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:138 deleteBook`, 204 at :153 |
| R7 | Data stored in SQLite | ✓ implemented | `go-sqlite3` import; `newAPI` CREATE TABLE :36 |
| R8 | JSON + correct status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/404/400/204 |
| R9 | Validate title & author required | ✓ implemented | `main.go:192`; test `TestCreateRequiresTitleAndAuthor` |
| R10 | GET /health | ✓ implemented | `main.go:60 health`; test `TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` (Run/Endpoints/Test sections) |
| R12 | ≥3 tests | ✓ implemented | 4 tests in `main_test.go`; test_coverage=0.631 |

## Build & Test

Not re-run — stored scores used (per skill Step 2):

```text
scores.json: defect_rate=1.0 (build+test passed), test_coverage=0.631 (coverage),
code_quality=0.956, maintainability=0.943, idiomatic=0.62
```

4 tests present, 0 skipped (`grep t.Skip` → 0). All exercised via `httptest` against an in-memory SQLite DB.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-blank) | 210 (main.go) |
| Test LOC (non-blank) | 87 (main_test.go) |
| Files | 12 |
| Dependencies (go.sum entries) | 2 (mattn/go-sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 63.1% |

## Findings

None. Clean, complete, idiomatic implementation with all endpoints, validation,
SQLite persistence, health check, README, and passing tests. Uses Go 1.22+
`net/http` method+path routing (`GET /books/{id}`) and parameterized SQL.

## Reproduce

```bash
cd "runs/agent=codex_effort=low_language=go_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json          # stored build/test/lint scores (not re-run)
grep -rE "t\.Skip\(" . --include="*.go" | wc -l   # 0 skips
go test ./...            # optional: 4 tests pass
```
