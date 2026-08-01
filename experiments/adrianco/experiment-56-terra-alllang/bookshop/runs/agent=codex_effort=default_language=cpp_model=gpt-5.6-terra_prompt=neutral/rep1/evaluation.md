# Evaluation: language=cpp_model=gpt-5.6-terra_agent=codex_prompt=neutral · rep 1

## Summary

- **Factors:** language=cpp, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passed (test_coverage=1.0 from scores.json) / 0 failed / 0 skipped (integration driver, 6 assertions)
- **Build:** pass — from scores.json (defect_rate=1.0 ⇒ build+test succeeded)
- **Lint:** pass — code_quality=1.0 from scores.json (`-Wall -Wextra -Wpedantic`)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_service.cpp:116 create_book`, routed at :103; returns 201 with body |
| R2 | GET /books lists all books | ✓ implemented | `book_service.cpp:131 list_books`; JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `book_service.cpp:132-134` binds author to `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `book_service.cpp:140 get_book`; `parse_id` :66, 404 when absent :142 |
| R5 | PUT /books/{id} updates | ✓ implemented | `book_service.cpp:146 update_book`; 404 if missing :147 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `book_service.cpp:160 delete_book`; 204 on success, 404 otherwise :163 |
| R7 | Data stored in SQLite | ✓ implemented | `book_service.cpp:94-97` opens sqlite3, `CREATE TABLE books`; `-lsqlite3` in Makefile |
| R8 | JSON responses + status codes | ✓ implemented | `book_json` :78, `error` :74; 201/200/204/400/404/500 across handlers; `Content-Type: application/json` main.cpp:33 |
| R9 | title & author required | ✓ implemented | `book_service.cpp:119` and :149 reject empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `book_service.cpp:102` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, API, tests, curl example |
| R12 | ≥3 tests | ✓ implemented | `tests.cpp` — 6 assertions (health/validation/create/filter/update/delete); test_coverage=1.0 |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=1.0
⇒ make (c++ -std=c++17 -Wall -Wextra -Wpedantic) built clean; make test passed.
```

Note: the agent's own post-build smoke test (a `make && curl` one-liner) was
rejected by the codex sandbox for containing `rm -f` (`_agent_stderr.log`), but
this did not affect the build/test gate — retort's scorers built and ran the
tests independently (test_coverage=1.0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 242 (book_service.cpp 164, main.cpp 36, hpp 27, tests.cpp 15) |
| Files | 4 source (+ Makefile, README) |
| Dependencies | 1 (system libsqlite3) |
| Tests total | 6 assertions (1 driver) |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium items.

1. [low] R3 `?author=` filter is not URL-decoded and consumes the rest of the query string (`book_service.cpp:132`) — functional for the tested exact-match case, degrades on encoded/multi-param queries.
2. [info] R12 tests are a single monolithic driver rather than discrete named cases (`tests.cpp:6`) — still exceeds the ≥3 requirement.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=cpp_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json          # stored mechanical scores (build/test/lint)
make && make test        # optional: rebuild + run the integration driver
```
