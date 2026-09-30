# Evaluation: effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — defect_rate=1.0 from retort.db (not re-run)
- **Lint:** pass — code_quality=0.79 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` / `retort.db` (not re-run): `defect_rate=1.0`
(build + tests pass), `test_coverage=0.97`, `requirement_coverage=1.0`,
`code_quality=0.79`, `maintainability=0.94`, `idiomatic=0.83`. Run completed in
23.4s over 6 turns, 103.5K tokens, $0.099.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:96 create()` → INSERT, 201; `main_test.go:34` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:110 list()` → SELECT ORDER BY id; `main_test.go:75` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:112-115` adds `WHERE author=?`; `main_test.go:71` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:134 get()` → 200/404; `main_test.go:38,47` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:152 update()` → UPDATE, 404 on 0 rows; `main_test.go:41,50` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:174 delete()` → DELETE, 204/404; `main_test.go:44` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:13,27` `modernc.org/sqlite`, CREATE TABLE books |
| R8 | JSON responses with correct status codes | ✓ implemented | `main.go:59 writeJSON`; 201/200/204/400/404/500 throughout |
| R9 | Validation: title and author required | ✓ implemented | `main.go:75-79 decode()` trims + 400; `main_test.go:55 TestValidation` |
| R10 | GET /health health check | ✓ implemented | `main.go:44-50` db-ping → 200/503; `main_test.go:26` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:1-18` run/test/endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 tests in `main_test.go`; test_coverage=0.97 |

No prompt-factor requirements: `prompts/neutral.md` prescribes no methodology
beyond "include tests" (already R12).

## Build & Test

Not re-run — stored scores used per skill policy.

```text
# from retort.db (run replicate 2, status=completed)
defect_rate       = 1.0   # build + all tests pass
test_coverage     = 0.97  # go test coverage
requirement_coverage = 1.0
```

Test surface (`go test ./...`, 4 functions, 0 skips):
```text
TestHealth       — GET /health → 200
TestCRUD         — create/get/update/delete lifecycle + 404 paths
TestValidation   — missing title/author, whitespace, bad JSON, bad id → 400
TestListFilter   — ?author= filter + full-list count
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 284 (main.go 206, main_test.go 78) |
| Files (excl. logs/git) | 6 (main.go, main_test.go, go.mod, go.sum, README.md, stack.json) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | 23.4s (full run wall-clock; build not separately timed) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no deductions:

1. [info] Negative-year validation beyond spec (`main.go:80`)
2. [info] Health check pings the DB rather than returning a static 200 (`main.go:44-50`)
3. [info] README omits an explicit `go mod download` step (`README.md:5-10`)

No critical/high/medium/low findings: every pinned requirement is implemented and
exercised by a passing test, with no skipped or disabled tests.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2
cat scores.json                      # stored mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" main_test.go   # 4 test functions
# build/test NOT re-run — defect_rate=1.0 in retort.db is the build+test signal
```
