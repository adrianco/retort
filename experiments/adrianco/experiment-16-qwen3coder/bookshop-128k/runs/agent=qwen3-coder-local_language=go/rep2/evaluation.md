# Evaluation: agent=qwen3-coder-local_language=go · rep 2

## Summary

- **Factors:** language=go, agent=qwen3-coder-local, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — from `scores.json` (defect_rate=1.0)
- **Lint:** pass — code_quality=0.9556 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 3 low, 1 info)

Mechanical scores (from `scores.json`): test_coverage=0.591, defect_rate=1.0,
code_quality=0.9556, maintainability=0.9425, idiomatic=0.68,
token_efficiency=0.0082. `defect_rate=1.0` confirms the build compiled and all
tests passed; `test_coverage=0.591` is line coverage, not a pass-rate failure.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:145` `createBook` inserts + returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:81` `getBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:87-95` LIKE filter; `TestGetBooksWithFilter` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:118` `getBook`, 404 at `main.go:134` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:189` `updateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:245` `deleteBook`, 204 at `main.go:276` |
| R7 | Data in SQLite | ✓ implemented | `main.go:12,49` go-sqlite3, `./books.db` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 set; success bodies JSON (error bodies are text — see Q1) |
| R9 | Validation: title & author required | ✓ implemented | `main.go:157,209` reject empty with 400 |
| R10 | GET /health | ✓ implemented | `main.go:75` returns `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — deps, `go run`, endpoints, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 `Test*` funcs in `main_test.go` |

## Build & Test

Not re-run — scores read from `scores.json` (per evaluate-run: do not re-run the
toolchain when stored scores exist).

```text
defect_rate = 1.0   → build + tests succeeded
test_coverage = 0.591 → 8 tests executed and passed (line coverage 59.1%)
code_quality = 0.9556
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go) | 277 |
| Test LOC (main_test.go) | 402 |
| Files (source) | 2 Go + README + go.mod/go.sum |
| Dependencies (go.sum entries) | 4 (gorilla/mux, mattn/go-sqlite3) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] Q1 — Error responses are plain text, not JSON (`http.Error` at `main.go:97,108,125,165`)
2. [low] Q2 — SQL not-found detected by string-comparing the error message (`main.go:133,218,260`)
3. [low] Q3 — Empty book list serializes as JSON `null` instead of `[]` (`main.go:103`)
4. [low] Q4 — Author filter is an unanchored LIKE substring match (`main.go:89-95`)
5. [info] eff-1 — Very low token efficiency; ~355 MB agent transcript (`scores.json`)

No critical or high findings — the run is a clean, spec-complete implementation
with all tests passing.

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-128k/runs/agent=qwen3-coder-local_language=go/rep2
cat scores.json            # stored mechanical scores (build/test/lint)
grep -cE "^func Test" main_test.go   # 8 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# Optional full re-run:
go test -v ./...
```
