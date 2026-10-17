# Evaluation: effort=max language=go model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** build + tests pass (defect_rate=1.0); 19 test functions, 0 skipped (all effective); line coverage 75.5%
- **Build:** pass (from retort.db/scores.json — not re-run)
- **Lint:** pass — code_quality=1.0
- **Architecture:** `run-summary` skill unavailable in this session — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Stored scores (from `scores.json`, not re-run): `code_quality=1.0`, `test_coverage=0.755`,
`defect_rate=1.0`, `maintainability=0.874`, `idiomatic=0.92`, `token_efficiency=0.0033`.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `internal/api/api.go:103` createBook → `internal/store/store.go:71` Create (201 + Location) |
| R2 | GET /books lists all | ✓ implemented | `internal/api/api.go:93` listBooks → `store.go:102` List |
| R3 | GET /books ?author= filter | ✓ implemented | `api.go:94` reads `author`; `store.go:106` case-insensitive `instr` filter; test `api_test.go:221` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `api.go:117` getBook; `store.go:91` maps no-rows → ErrNotFound → 404 (`api.go:124`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `api.go:134` updateBook → `store.go:134` Update (full-replace, 404 on missing) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `api.go:154` deleteBook → `store.go:152` Delete (204, 404 on missing) |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `store.go:14` modernc.org/sqlite (pure-Go); schema `store.go:21`; persistence test `store_test.go:122` |
| R8 | JSON responses + correct codes | ✓ implemented | `api.go:226` writeJSON sets Content-Type; 201/200/204/400/404/405/413/503 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `internal/book/book.go:54` Validate → 400; test `api_test.go:145` TestCreateRejectsInvalidBooks |
| R10 | GET /health | ✓ implemented | `api.go:81` health (pings DB; 200/503); test `api_test.go:329` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Requirements, Setup, Run, config table, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 19 `func Test*` across api/book/store; `test_coverage=0.755 > 0` |

No requirement is missing or partial. Enhancements beyond spec are recorded as info findings
(health DB-ping, body-size/ISBN/length hardening, documented full-replace PUT).

## Build & Test

Not re-run — per skill, stored mechanical scores stand in for the toolchain:

```text
scores.json: defect_rate=1.0  => go build + go test succeeded
scores.json: test_coverage=0.755  => tests executed; 75.5% line coverage
scores.json: code_quality=1.0  => lint/quality clean
```

Skip scan (`grep -rnE "t\.Skip|t\.Skipf|testing\.Short" --include="*.go"`): no matches —
0 skipped tests, so all 19 test functions (plus table subtests) are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test .go) | 618 |
| Lines of code (tests) | 740 |
| Files (excl. .git) | 19 |
| Dependencies (go.sum lines) | 50 (1 direct: modernc.org/sqlite) |
| Tests total (func Test*) | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no deductions:

1. [info] E1 — Health check verifies DB reachability, not just process liveness
2. [info] E2 — Input hardening beyond the spec (body cap, ISBN/length checks)
3. [info] E3 — PUT uses documented full-replace semantics

## Reproduce

```bash
cd experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=go_model=claude-haiku-5-5_prompt=neutral/rep3
cat scores.json                                   # stored mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                    # pinned 12-item checklist
grep -rn "^func Test" --include="*.go" .          # 19 test functions
grep -rnE "t\.Skip|t\.Skipf|testing\.Short" --include="*.go" .   # none -> 0 skips
find . -name "*.go" -not -name "*_test.go" | xargs wc -l   # 618 source LOC
```
