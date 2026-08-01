# Evaluation: language=objc · agent=codex · model=gpt-5.6-terra · prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` (build + tests succeeded via `make test`)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session — see notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

Denominator pinned by `bookshop/REQUIREMENTS.json` (12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.m:80-83` → `BookStore.m:95-107` `createBook:` |
| R2 | GET /books lists all | ✓ implemented | `main.m:71-79` → `BookStore.m:74-84` `allBooksByAuthor:` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.m:72-77` parses `author`; `BookStore.m:75` WHERE author=? |
| R4 | GET /books/{id} single | ✓ implemented | `main.m:89-92`, 404 when nil; `BookStore.m:86-93` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.m:93-96` → `BookStore.m:109-126` merge+validate |
| R6 | DELETE /books/{id} | ✓ implemented | `main.m:97-100` → `BookStore.m:128-137`, 404 when no row changed |
| R7 | SQLite storage | ✓ implemented | `BookStore.m:2,16-24` opens sqlite3, CREATE TABLE books |
| R8 | JSON + status codes | ✓ implemented | `main.m:16-24` `sendResponse`; 201/200/204/400/404/405/500 |
| R9 | title & author required | ✓ implemented | `BookStore.m:40-59` `validate:` returns 400 on empty |
| R10 | GET /health | ✓ implemented | `main.m:69` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, endpoints, curl examples |
| R12 | ≥3 tests | ✓ implemented | `tests.m:12-21` — 7 assertions; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 1.0   → make test: clang build + ./book-api-tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build + test succeeded
```

Test harness (`tests.m`) drives the `BookStore` data layer through the full CRUD
lifecycle: create, required-field rejection (400), author filter, update-with-retain,
delete, and post-delete fetch.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 355 (incl. README/Makefile) |
| Files | 14 (excl. build/module cache) |
| Dependencies | 0 third-party (Foundation + libsqlite3 only) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| token_efficiency | 0.0200 |
| maintainability | 0.567 |
| idiomatic | 0.70 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Tests exercise the `BookStore` layer only, not HTTP routing/status mapping in `main.m`
2. [info] Self-contained BSD-socket HTTP server, no third-party framework
3. [info] PUT preserves untouched fields (partial update beyond bare spec)

No critical or high findings. `min_severity=high` → assessment penalty_score = 1.0.

## Notes

- The agent's `_agent_stderr.log` shows one rejected `rm -f` cleanup command (sandbox
  policy), which did not affect the delivered artifacts — the build, tests, and all
  source files are present and passing.
- `run-summary` skill is not available in this session; architecture is summarized
  inline above rather than under `summary/`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=objc_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (source of build/test/lint)
make test                       # clang build + ./book-api-tests (fallback verification)
```
