# Evaluation: agent=codex effort=low language=cpp model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=cpp, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 scenarios passed / 0 failed / 0 skipped (7 effective; 1 registered ctest target)
- **Build:** pass — from `test_coverage=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.806` (scores.json); not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Scores (from `scores.json`, scored inline): test_coverage=1.0, code_quality=0.806,
defect_rate=0.0, maintainability=0.632, idiomatic=0.2, token_efficiency=0.0023.
The low idiomatic score reflects the extremely dense one-statement-per-line style, not
a functional defect. All 12 pinned requirements (`REQUIREMENTS.json`) are satisfied.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.cpp:36` INSERT; `tests.cpp:7` 201 |
| R2 | GET /books lists all | ✓ implemented | `main.cpp:35` SELECT all; `tests.cpp:8` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.cpp:35` parses `author=`, WHERE author=?; `tests.cpp:8` |
| R4 | GET /books/{id} single | ✓ implemented | `main.cpp:37` GET branch, 404 if absent; `tests.cpp:10,12` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.cpp:37` UPDATE, 404 if no change; `tests.cpp:11` |
| R6 | DELETE /books/{id} | ✓ implemented | `main.cpp:37` DELETE, 204/404; `tests.cpp:12` |
| R7 | Stored in SQLite | ✓ implemented | `main.cpp:25-31` `Store` + prepared stmts |
| R8 | JSON responses + status codes | ✓ implemented | `main.cpp:43` `serve_client` JSON + 200/201/204/400/404 |
| R9 | Validation: title & author required | ✓ implemented | `main.cpp:36` trim-empty check → 400; `tests.cpp:9` |
| R10 | GET /health | ✓ implemented | `main.cpp:34` returns `{"status":"ok"}`; `tests.cpp:13` |
| R11 | README with setup/run | ✓ implemented | `README.md` build/run/test + endpoints |
| R12 | >= 3 tests | ✓ implemented | `tests.cpp` 7 assert scenarios; `test_coverage=1.0` |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (compiled-language re-run is
pure duplication).

```text
test_coverage = 1.0   # build succeeded + all tests passed (scores.json)
code_quality  = 0.806 # lint/quality (scores.json)
```

Build: `cmake -S . -B build && cmake --build build` (CMakeLists.txt). Tests:
`ctest --test-dir build` — one target `book_api_tests` with 7 assertions covering the
full CRUD + filter + validation + health path (`tests.cpp:6-13`). 0 skips
(`grep` for DISABLED_/GTEST_SKIP → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | main.cpp 44, tests.cpp 13, CMakeLists.txt 16 |
| Files (excl. build artifacts) | 7 (main.cpp, tests.cpp, CMakeLists.txt, README.md, TASK.md, stack.json, scores.json) |
| Dependencies | sqlite3, json-c (system libs via find_package/pkg-config) |
| Tests total | 7 scenarios (1 ctest target) |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R12 — all 7 test scenarios live in one assert-based binary; first failing assert aborts the rest (`tests.cpp:6-13`).
2. [low] POST/PUT require `year` as a present int, stricter than the spec's "title and author are required" (`main.cpp:36`).
3. [info] Single-threaded blocking server (`main.cpp:44`).

No critical, high, or medium findings — the run fully implements the spec and passes build + tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=cpp_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                      # test_coverage=1.0 (build+tests), code_quality=0.806
cat ../../../REQUIREMENTS.json       # pinned 12-requirement checklist
grep -rE "DISABLED_|GTEST_SKIP" . --include="*.cpp" | grep -v build-warn   # 0 skips
# build/test NOT re-run — stored scores used per the evaluate-run skill
```
