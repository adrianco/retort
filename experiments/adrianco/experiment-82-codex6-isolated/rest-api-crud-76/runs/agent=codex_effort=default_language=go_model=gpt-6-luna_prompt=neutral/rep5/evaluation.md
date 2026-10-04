# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=0.584`
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.9556` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:59-77` INSERT of all four fields; `TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:86-113` `listBooks`; `TestListFiltersByAuthor` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:87-92`; `TestListFiltersByAuthor` asserts single result |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:124-129` + `notFoundOrError` `main.go:188-194`; `TestValidationAndUpdateDelete` checks 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:130-151` (0 rows → 404); `TestValidationAndUpdateDelete` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:152-163` (204, 0 rows → 404); `TestValidationAndUpdateDelete` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:14` `go-sqlite3`, `main.go:31-39` table DDL, `main.go:209` `sql.Open("sqlite3", …)` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:195-202`; 201/200/204/400/404/500/503 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `validBook` `main.go:181-187` → 400; `TestValidationAndUpdateDelete` asserts 400 |
| R10 | GET /health endpoint | ✓ implemented | `main.go:45-51` pings DB; `TestHealth` asserts 200 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Run (`go run .`), env vars, endpoints, Test section |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 `func Test*` in `main_test.go`; `test_coverage=0.584 > 0` |

## Build & Test

Not re-run — stored scores used per skill (scores.json):

```text
defect_rate    = 1.0     # build + tests succeeded
test_coverage  = 0.584   # tests executed; 58.4% statement coverage
code_quality   = 0.9556
maintainability= 0.9385
idiomatic      = 0.45
token_efficiency = 0.0286
```

Test suite (`go test ./...`), 4 functions, 0 skips:
`TestCreateAndGetBook`, `TestListFiltersByAuthor`, `TestValidationAndUpdateDelete`, `TestHealth`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 321 (main.go 224 + main_test.go 97) |
| Files (source) | 2 (`main.go`, `main_test.go`) |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3 v1.14.24`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Statement coverage | 58.4% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Error/edge paths untested (coverage 0.584) — 500/503 branches have no tests
2. [info] Hardened JSON decoding beyond spec (DisallowUnknownFields, 1 MiB limit, single-object guard)
3. [info] Path id bound to SQL as string; non-numeric ids yield 404 rather than 400

No critical/high/medium findings. All 12 pinned requirements implemented; build and tests pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep5"
cat scores.json            # stored build/test/lint scores (not re-run)
grep -rEc "t\.Skip" . --include="*.go"   # 0 skips
grep -rE "^func Test" main_test.go | wc -l   # 4 tests
# (optional live check) go test ./...
```
