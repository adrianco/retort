# Evaluation: effort=low language=go model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=low, prompt=neutral, agent=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions (all passed) / 0 failed / 0 skipped (6 effective) — `test_coverage=0.789` from `scores.json`
- **Build:** pass — `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json`, 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:76 createBook` → `store.go:65 Create`, 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:90 listBooks` → `store.go:98 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:91` passes query param; `store.go:101-104 WHERE author = ?` |
| R4 | GET /books/{id} single book | ✓ implemented | `handlers.go:99 getBook`; 404 via `writeStoreError` `handlers.go:188` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:112 updateBook` → `store.go:128 Update` (404 if absent) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:129 deleteBook` → `store.go:147 Delete`, 204 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8 modernc.org/sqlite`, schema `store.go:39-46` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `handlers.go:199`; 201/200/404/400/204/413/503 used |
| R9 | Validation: title+author required | ✓ implemented | `bookInput.Validate` `handlers.go:30-37`; test `TestCreateValidation` |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:68 health` pings DB, returns `{status:ok}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | >= 3 tests | ✓ implemented | `server_test.go` — 6 test funcs; `test_coverage=0.789 > 0` |

## Build & Test

Scores read from `scores.json` (computed by retort's scorers; not re-run per the skill):

```text
code_quality      = 1.0     (lint: pass, 0 warnings)
test_coverage     = 0.789   (build + tests ran and passed; 78.9% coverage)
defect_rate       = 1.0     (build + test succeeded)
maintainability   = 0.838
idiomatic         = 0.85
token_efficiency  = 0.040
```

Skip scan (`grep -rE "t\.Skip\(|t\.Skipf\("`): 0 — no skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 587 (main 33, store 160, handlers 203, test 191) |
| Files | 11 (incl. go.mod/go.sum/README; excl. `_agent_*`/caches) |
| Dependencies (go.sum lines) | 50 |
| Tests total | 6 functions (TestCreateValidation has 4 subcases) |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Validation and hardening beyond spec — year range, `DisallowUnknownFields`, 1 MiB body cap, Location header (`handlers.go`)
2. [info] Author filter is exact-match only (`store.go:102`) — satisfies R3 as written

No requirement gaps, build failures, test failures, or skipped tests. This is a clean, fully-conformant run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=go_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores
cat ../../REQUIREMENTS.json                        # pinned 12-requirement checklist
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip scan -> 0
# (build/test NOT re-run: scores.json authoritative, per evaluate-run skill)
```
