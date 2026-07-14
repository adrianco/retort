# Evaluation: agent=hermes-local language=go prompt=neutral · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (Gin), prompt=neutral
- **Status:** ok — builds and all tests pass; endpoints served under an `/api` prefix instead of the spec's root paths
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator = 12)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — per `_agent_stdout.log` "11 tests, 0 failures", `defect_rate=1.0`
- **Build:** pass — inferred from `defect_rate=1.0` and `test_coverage=0.545` in `scores.json` (tests can't run without a successful build)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low, 1 info)

Scores read from `scores.json` (no re-run): test_coverage=0.545, code_quality=0.9556,
defect_rate=1.0, maintainability=0.8846, idiomatic=0.42, token_efficiency=0.0047.

## Requirements

Checklist is the pinned `bookshop/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:68 CreateBook` — INSERT, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.go:120 GetBooks` — SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:121-146` — WHERE author = ? |
| R4 | GET /books/{id} single book | ✓ implemented | `app.go:175 GetBook` — 404 on ErrNoRows |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:208 UpdateBook` — UPDATE, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:272 DeleteBook` — DELETE, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:44` go-sqlite3, `./books.db`, real table |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `app.go:79-91` + binding:required |
| R10 | GET /health health check | ✓ implemented | `app.go:308 HealthCheck` (served at /api/health) |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `app_test.go` — 11 tests, test_coverage>0 |

All 12 how-to-verify criteria are met. The `/api` path prefix (R1–R6, R10) and the
over-strict year/isbn validation (R9) are conformance deviations captured as findings,
not requirement gaps.

## Build & Test

Not re-run — scores taken from `scores.json` (per skill: `test_coverage`/`defect_rate`
stand in for build+test).

```text
scores.json: {"test_coverage":0.545, "defect_rate":1.0, "code_quality":0.9556, ...}
_agent_stdout.log: "The tests pass (11 tests, 0 failures)"
```

- `defect_rate=1.0` ⇒ build + tests succeeded.
- `test_coverage=0.545` ⇒ ~54.5% line coverage; the uncovered ~45% is chiefly `main()`
  and the `/api` route registration, which no test invokes (see finding `routes-untested`).
- Skip scan: `grep -rE "t\.Skip\(|t\.Skipf\("` → 0 skips. All 11 tests are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 717 (app.go 351, app_test.go 366) |
| Files (excl. binary + books.db) | 13 |
| Dependencies (go.sum module lines / direct requires) | 91 / 29 |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Line coverage | 54.5% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] All endpoints served under `/api` prefix, not the spec's root paths (`app.go:329-339`)
2. [medium] Production route wiring (main's `/api` group) is not covered by any test (`app_test.go:39-52`)
3. [low] `year` and `isbn` required beyond the spec's title/author (`app.go:28-29`)
4. [low] Tests build id path via `string(rune(id+'0'))`, only correct for ids 1–9 (`app_test.go:240,289,339`)
5. [info] Explicit empty title/author checks unreachable after `binding:required` (`app.go:79-91`)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep3
cat scores.json                                   # stored build/test/lint scores (do not re-run)
grep -rEn "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -c "^func Test" app_test.go                  # 11 tests
# optional live check: go test -v   (builds + runs; ~54.5% coverage)
```
