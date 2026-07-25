# Evaluation: language=c_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-opus-5, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (one low-severity note on R9's status code)
- **Tests:** all passed / 0 failed / 0 skipped (19 test functions, README reports 276 checks across 3 suites)
- **Build:** pass — via `test_coverage=1.0` in scores.json (build + tests both ran and passed)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/api.c:152 handle_create` → `db_create`, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `src/api.c:125 handle_list` → `db_list(ctx,NULL,..)` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/api.c:133 http_query_get("author")` → `db_list(ctx, filter, ..)` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/api.c:187 handle_get_one` → DB_NOT_FOUND→404 |
| R5 | PUT /books/{id} update | ✓ implemented | `src/api.c:205 handle_update` → `db_update`, full-replace semantics |
| R6 | DELETE /books/{id} | ✓ implemented | `src/api.c:243 handle_delete` → 204 / 404 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/db.c:3 #include <sqlite3.h>`; schema at `src/db.c:17`; `Makefile:6 -lsqlite3` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/204/404/400/409/422/503 across `src/api.c`; `book_to_json` |
| R9 | Validate title & author required | ✓ implemented | `src/book_json.c:182-183 take_required_string`; rejects (422 — see finding) |
| R10 | GET /health | ✓ implemented | `src/api.c:77 handle_health` — touches DB, 503 if unavailable |
| R11 | README with setup/run | ✓ implemented | `README.md:11-37` deps, build, run, curl examples |
| R12 | >= 3 tests | ✓ implemented | 19 test funcs across `tests/test_api.c`, `test_db.c`, `test_json.c`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
idiomatic     = 0.88
maintainability = 0.66
token_efficiency = 0.017
```

No skipped/disabled tests (`grep` for SKIP/#if 0 in tests/ → 0 hits).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src + tests, .c/.h) | 4,298 |
| Files (src + tests) | 17 |
| Dependencies | 1 external (sqlite3) |
| Test functions | 19 |
| Tests effective | 19 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — missing-field validation returns 422, not the 400 the spec example cites (malformed JSON does return 400). Semantically defensible; noted for strict conformance.
2. [info] Health check verifies the DB (503 on failure), not just liveness — beyond spec.
3. [info] Integration tests drive the real binary over TCP incl. a restart-durability check — far exceeds the ≥3-tests bar.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-46-opus5/bookshop/runs/language=c_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                    # stored build/test/lint scores
cat ../../../REQUIREMENTS.json     # pinned requirement checklist
grep -rn 'sqlite' src/db.c Makefile
grep -rhoE 'static void test_[a-z_]+' tests/*.c | sort -u   # 19 test funcs
make test                          # optional: rebuild + run suites
```
