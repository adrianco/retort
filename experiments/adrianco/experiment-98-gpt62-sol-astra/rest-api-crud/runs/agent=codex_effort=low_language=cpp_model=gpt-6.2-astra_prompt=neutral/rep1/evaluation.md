# Evaluation: agent=codex effort=low language=cpp model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (Boost.Beast chosen)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ build + all tests succeeded (not re-run; cited from scores)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant 12-item denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `api.hpp:140` INSERT branch binds all four fields, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `api.hpp:108` `SELECT ... ORDER BY id` → JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `api.hpp:100-108` parses `author` query, uses `WHERE author=?`; test `GET /books?author=A+%26+B` |
| R4 | GET /books/{id} single book | ✓ implemented | `api.hpp:118` `WHERE id=?`, 404 via `missing()` when absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.hpp:135` UPDATE branch, 404 if `sqlite3_changes==0` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.hpp:124` DELETE, returns `{deleted:id}` or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `api.hpp:168` `open_database` + `CREATE TABLE books`; `#include <sqlite3.h>` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `reply()` sets `application/json`; 201/200/404/400/405/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `api.hpp:146` nonblank-string check throws `BadInput`→400; `test_validation` matrix |
| R10 | GET /health | ✓ implemented | `api.hpp:91` returns `{status:"ok"}`; `test_health_and_routing` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build steps, deps, curl examples, route table |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests.py` has 4 test methods; `test_coverage=1.0` |

No requirement is partial or missing.

## Build & Test

Build and tests were **not re-run** — stored mechanical scores are authoritative (per evaluate-run skill):

```text
scores.json: {"code_quality": 0.9556, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.5043, "idiomatic": 0.45, "token_efficiency": 0.0245}
test_coverage=1.0  ⇒  cmake build succeeded AND all ctest tests passed
defect_rate=1.0    ⇒  build+test success confirmed
```

Test suite (`tests.py`, driven via the `test_transport` socket shim): `test_crud`,
`test_list_filter_and_persistence`, `test_validation`, `test_health_and_routing` — 4 methods,
0 skips (`grep` for skip/xfail/GTEST_SKIP → 0 matches).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 327 (api.hpp 198, main.cpp 20, test_transport.cpp 12, tests.py 74, CMakeLists 23) |
| Files | 13 (excl. build-warn) |
| Dependencies | Boost.Beast/JSON, SQLite3, Threads, Python3 (tests) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores cited) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational enhancements, none affect conformance:

1. [info] No pagination on GET /books (not required by spec) — `api.hpp:98`
2. [info] Single-threaded, blocking accept loop — `main.cpp:11`
3. [info] Tests are integration-level only; no isolated unit tests of helpers — `tests.py:1`

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=cpp_model=gpt-6.2-astra_prompt=neutral/rep1
cat scores.json                                   # mechanical scores (build/test/lint) — do not re-run
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rEc "skip|xfail|GTEST_SKIP" tests.py *.cpp   # skip detection → 0
grep -c "def test_" tests.py                        # 4 test methods
```
