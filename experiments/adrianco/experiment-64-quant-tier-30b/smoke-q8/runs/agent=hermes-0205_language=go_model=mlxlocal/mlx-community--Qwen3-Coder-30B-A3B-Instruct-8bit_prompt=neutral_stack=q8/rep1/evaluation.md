# Evaluation: agent=hermes-0205 · go · Qwen3-Coder-30B-8bit (q8) · rep 1

## Summary

- **Factors:** language=go, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `defect_rate=1.0` confirms build+tests ran and passed
- **Build:** pass (from `scores.json` `defect_rate=1.0`; not re-run)
- **Lint:** pass — `code_quality=0.9556` (from `scores.json`)
- **Coverage:** `test_coverage=0.295` — tests execute but exercise a minority of the CRUD paths
- **Architecture:** single `main.go` REST service, stdlib `net/http` routing, `mattn/go-sqlite3` persistence; run-summary skill unavailable this session
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 4 low, 1 info)

## Requirements

Scored against the pinned `smoke-q8/REQUIREMENTS.json` (constant 12-item denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:123` createBookHandler; tested `main_test.go:43` |
| R2 | GET /books lists all | ✓ implemented | `main.go:60` getBooksHandler; tested `main_test.go:104` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:63-72` LIKE filter (untested) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:96-120` incl. `sql.ErrNoRows`→404 |
| R5 | PUT /books/{id} update | ✓ implemented | `main.go:158-204` updateBookHandler |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:207-239`, returns 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:29-50` initDB, `mattn/go-sqlite3` |
| R8 | JSON + status codes | ✓ implemented | 201/200/404/400/204 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `main.go:133`, `main.go:176`; tested `main_test.go:85` |
| R10 | GET /health | ✓ implemented | `main.go:53-57`; tested `main_test.go:23` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, curl examples) |
| R12 | ≥3 tests | ✓ implemented | 4 test funcs; `test_coverage=0.295>0` |

## Build & Test

Not re-run — stored mechanical scores used per skill:

```text
# from scores.json (inline gate)
defect_rate=1.0        # build + tests passed
test_coverage=0.295    # coverage fraction
code_quality=0.9556
maintainability=0.883  idiomatic=0.42
```

Tests: `TestHealthCheck`, `TestCreateBook`, `TestCreateBookMissingFields`, `TestGetBooks` (+ `TestMain` harness). 0 `t.Skip` calls found.

Note: the DB row for this cell (`retort.db` run id 1) reports different values (`test_coverage=0.92`, `code_quality=0.789`, `idiomatic=0.7`, `requirement_coverage=1.0`); `scores.json` is the archive's own inline-gate scores and is used here per the skill's stated priority.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 403 (main.go 285, main_test.go 118) |
| Files | 15 (incl. logs/session artifacts) |
| Dependencies | 1 direct (`mattn/go-sqlite3`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Turns / API calls | 59 / 62 |
| Duration | ~606 s |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] Low test coverage (0.295) — CRUD read/update/delete/filter paths untested
2. [medium] Tests share a persistent `./books.db` with no cleanup or isolation (`main_test.go:12`)
3. [low] R3 author filter implemented but not covered by a test
4. [low] R4 get-by-id implemented but not covered by a test
5. [low] R5/R6 update & delete implemented but not covered by tests

## Reproduce

```bash
cd "experiments/adrianco/experiment-64-quant-tier-30b/smoke-q8/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep1"
cat scores.json                     # stored mechanical scores (no re-run)
cat ../../../../REQUIREMENTS.json    # pinned R1–R12 checklist
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
```
