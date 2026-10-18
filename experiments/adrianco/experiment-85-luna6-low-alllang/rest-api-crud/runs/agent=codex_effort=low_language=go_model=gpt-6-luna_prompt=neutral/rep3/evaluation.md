# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib `net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `defect_rate=1.0` (build + tests pass); line coverage `test_coverage=0.603`
- **Build:** pass — not re-run (from `scores.json`: `defect_rate=1.0`)
- **Lint:** pass — not re-run (from `scores.json`: `code_quality=0.956`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate output); the toolchain was **not**
re-run per the skill's don't-re-run rule.

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:84 API.create` INSERTs all four fields |
| R2 | GET /books lists all books | ✓ implemented | `main.go:106 API.list` SELECT + JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:108` adds `WHERE author = ?`; tested `main_test.go:92` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:147` GET case; 404 at `main.go:150` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:158` UPDATE; 404 on 0 rows `main.go:173` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:179` DELETE; 204/404 `main.go:186,190` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `modernc.org/sqlite` (`main.go:17`), CREATE TABLE `main.go:31` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:228`; 201/200/204/400/404/500 |
| R9 | Input validation: title & author required | ✓ implemented | `validate` `main.go:202`; tested `main_test.go:103` |
| R10 | GET /health health-check | ✓ implemented | `main.go:58`; tested `main_test.go:109 TestHealth` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Run/Endpoints/Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `func Test*` in `main_test.go`; pass (`defect_rate=1.0`) |

Prompt factor `neutral` adds no checkable instruction beyond "include tests"
(satisfied by R12).

## Build & Test

Not re-run (scores already computed). From `scores.json`:

```text
defect_rate      = 1.0     # go build + go test ./... succeeded
test_coverage    = 0.603   # statement coverage
code_quality     = 0.956   # vet/lint
maintainability  = 0.938
idiomatic        = 0.82
token_efficiency = 0.0156
```

3 test functions, 0 `t.Skip` calls. Coverage of 60.3% reflects untested error
branches (not-found on PUT/DELETE, invalid id, method-not-allowed) — all core
happy paths and the author filter / validation are exercised.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + test) | 375 |
| Files (excl .git) | 12 |
| Dependencies (go.sum entries) | 20 |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Strict JSON decoding beyond spec — `main.go:212`
2. [info] Configurable listen address and DB path — `main.go:241,254`

No correctness, requirement, build, or test findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores
grep -rnE "^func Test" . --include="*.go"         # 3 tests
grep -rcE "t\.Skip\(|t\.Skipf\(" main_test.go     # 0 skips
# (optional, re-verify) go test ./... -cover
```
