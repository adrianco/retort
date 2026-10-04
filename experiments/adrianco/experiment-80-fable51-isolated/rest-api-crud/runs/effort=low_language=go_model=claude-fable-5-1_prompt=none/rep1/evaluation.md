# Evaluation: effort=low_language=go_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=go, model=claude-fable-5-1, effort=low, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from stored scores (`defect_rate=1.0`, `test_coverage=0.744`); not re-run
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (skill step 2 — build/test/lint not re-run):
`test_coverage=0.744`, `code_quality=0.9556`, `defect_rate=1.0`, `maintainability=0.9788`,
`idiomatic=0.75`, `token_efficiency=0.089`. `defect_rate=1.0` and `test_coverage>0` confirm
the build succeeded and all tests executed and passed.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 fixed requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:118 createBook` — INSERT of all 4 fields, 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:135 listBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:138-141` WHERE author=?; `TestListAndAuthorFilter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:164 getBook`; 404 at `main.go:173` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:184 updateBook`; 404 when 0 rows |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:208 deleteBook`; 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:14,43-62` modernc.org/sqlite, real table |
| R8 | JSON responses + correct status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:83-91`; 201/200/204/400/404/500 |
| R9 | Validation: title & author required | ✓ implemented | `main.go:25-36 validate`; `TestValidation` |
| R10 | GET /health health check | ✓ implemented | `main.go:68-74`; `TestHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, env vars, endpoints, curl, tests |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `main_test.go` — 5 tests; `test_coverage=0.744>0` |

No prompt-factor requirements (`prompt=none`).

## Build & Test

Not re-run per skill step 2 — stored scores used:

```text
scores.json: defect_rate=1.0, test_coverage=0.744  => build + all tests passed
grep t.Skip/t.Skipf: none  => 0 skipped tests
5 test functions in main_test.go, all effective
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 362 (main.go 241 + main_test.go 121) |
| Files | 6 (main.go, main_test.go, go.mod, go.sum, README.md, .gitignore) |
| Dependencies | 1 direct (modernc.org/sqlite), 9 indirect |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; stored scores) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] POST /books sets a Location header (enhancement)
2. [info] Health check verifies DB connectivity, returns 503 when down (enhancement)
3. [info] Request body bounded via http.MaxBytesReader (enhancement)

No defects: all 12 requirements implemented, build and tests pass, zero skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=go_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json                     # pinned 12-requirement checklist
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # skipped-test count (0)
# to re-verify from scratch (optional): go test ./...
```
