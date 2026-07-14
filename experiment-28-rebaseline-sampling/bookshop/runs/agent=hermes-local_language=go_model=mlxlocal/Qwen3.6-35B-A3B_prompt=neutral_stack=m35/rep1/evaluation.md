# Evaluation: hermes-local · go · mlxlocal/Qwen3.6-35B-A3B · neutral · m35 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35, framework=gin
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — from defect_rate=1.0
- **Build:** pass (defect_rate=1.0 from scores.json; not re-run)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.go:86 createBookHandler`, INSERT at `app.go:103` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:125 listBooksHandler`, SELECT at `app.go:134` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.go:126,132` — `WHERE author = ?`; tested `app_test.go:213` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.go:165 getBookHandler`, 404 at `app.go:177` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:190 updateBookHandler`, UPDATE at `app.go:240` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:261 deleteBookHandler`, DELETE at `app.go:269` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:45 sql.Open("sqlite3", ...)`, table DDL `app.go:50` |
| R8 | JSON responses with correct status codes | ✓ implemented | `c.JSON` with 201/200/400/404/500 throughout `app.go` |
| R9 | Validation: title and author required | ✓ implemented | `app.go:68 validateBook`; tested `app_test.go:153 TestCreateBookValidation` |
| R10 | GET /health health check | ✓ implemented | `app.go:81 healthHandler`, route `app.go:295`; tested `app_test.go:100` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:47-75` setup/run/test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 `Test*` funcs in `app_test.go`; test_coverage=0.576 > 0 |

No requirements partial or missing. No enhancements beyond spec noted (year default is a minor quirk, see findings).

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
defect_rate      = 1.0     -> build + all tests passed
test_coverage    = 0.576   -> 57.6% line coverage (tests executed)
code_quality     = 0.9556
maintainability  = 0.9276
idiomatic        = 0.38
token_efficiency = 0.0246
```

Test inventory (`app_test.go`, 9 cases + `TestMain` harness): TestHealthCheck,
TestCreateBook, TestCreateBookValidation, TestListBooks, TestGetBook,
TestGetBookNotFound, TestUpdateBook, TestDeleteBook, TestDeleteBookNotFound.
Skip scan (`grep t.Skip`) = 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go + app_test.go) | 663 (310 + 353) |
| Files | 14 (incl. build/db artifacts) |
| Dependencies (go.sum lines) | 91 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Coverage | 57.6% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] year silently defaults to 2000 when omitted/zero — `app.go:98-101`
2. [low] tests mutate a package-level `db` global via handler wrappers — `app_test.go:67-86`
3. [info] list `?author=` filter is exact-match only — `app.go:132`
4. [info] coverage 57.6% — error/400 branches uncovered — `scores.json`

No high or critical findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-28-rebaseline-sampling/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep1
cat scores.json                                   # stored build/test/lint scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -cE "^func Test" app_test.go                 # 10 (incl. TestMain harness)
# build/test NOT re-run — defect_rate=1.0 in scores.json is authoritative
```
