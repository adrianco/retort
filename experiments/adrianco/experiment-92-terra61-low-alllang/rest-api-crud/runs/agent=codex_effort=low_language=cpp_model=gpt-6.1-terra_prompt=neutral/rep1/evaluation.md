# Evaluation: agent=codex effort=low language=cpp model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` / `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.78` in scores.json (not re-run)
- **Architecture:** single-file C++17 service (`main.cpp`, 162 LOC); libmicrohttpd + json-c + SQLite3; RAII wrappers (`std::unique_ptr`) for json-c and sqlite3 handles; `run-summary` skill not registered, summarized inline.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.cpp:99-133` INSERT with title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `main.cpp:69-78` SELECT … ORDER BY id, returns JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `main.cpp:70-73` binds `author` query arg to `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.cpp:80-88`, 404 at `:85` when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.cpp:99-133` UPDATE branch, 404 at `:127` if no row changed |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.cpp:89-98`, 404 at `:94` when no rows changed |
| R7 | SQLite / embedded DB | ✓ implemented | `main.cpp:153-155` opens sqlite3 DB, `CREATE TABLE books` |
| R8 | JSON responses + status codes | ✓ implemented | `main.cpp:18-26` JSON reply helper; 201/200/404/400/405/413/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `main.cpp:111-116` rejects missing/blank/non-string title/author with 400 |
| R10 | GET /health | ✓ implemented | `main.cpp:60-63` returns `{"status":"ok"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md:6-16` build + run + test instructions |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_api.py` 3 test methods; `test_coverage=1.0` |

## Build & Test

Build and test were **not re-run** — stored mechanical scores are authoritative:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.778
             maintainability=0.667  idiomatic=0.55  token_efficiency=0.0235
build-warn/book_service exists → compile succeeded
```

```text
test_api.py — 3 integration tests via ctest, driving the compiled binary over HTTP:
  test_lifecycle_and_filter     — POST/GET/filter/get-by-id/PUT/DELETE/404 round trip
  test_validation_and_missing_routes — 400 on bad input, 404/405 on bad routes, empty list
  test_persistence              — restart server, data survives (proves SQLite persistence)
0 skipped (no skip/xfail markers)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.cpp) | 162 |
| Lines of code (test_api.py) | 85 |
| Files (excl. build/logs) | 5 (main.cpp, test_api.py, CMakeLists.txt, README.md, TASK.md) |
| Dependencies | 3 (libmicrohttpd, json-c, SQLite3) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build | pass (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no deductions:

1. [info] Request body size cap (1 MiB) with 413 response — enhancement beyond spec
2. [info] 405 Method Not Allowed + strict trailing-content JSON rejection — stricter than required
3. [info] author filter is exact/case-sensitive — documented in README, acceptable per spec

No requirement is missing or partial; no test is skipped; build and tests pass.

## Reproduce

```bash
cd experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=cpp_model=gpt-6.1-terra_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -cE 'def test_' test_api.py      # 3 tests
grep -rE '\.skip|xfail|expectedFailure' test_api.py | wc -l   # 0 skips
# build/test already verified by retort scorers; binary at build-warn/book_service
```
