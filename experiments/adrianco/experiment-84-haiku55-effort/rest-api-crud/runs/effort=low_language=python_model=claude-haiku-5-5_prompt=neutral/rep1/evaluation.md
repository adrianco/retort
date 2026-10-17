# Evaluation: effort=low_language=python_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — `test_coverage=0.91`, `defect_rate=1.0` from scores.json
- **Build:** pass (not re-run — `defect_rate=1.0` ⇒ build+test succeeded)
- **Lint:** pass — `code_quality=0.6667` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.py:74 _create_book` → `book_store.py:97 create` |
| R2 | GET /books lists all | ✓ implemented | `server.py:66 _list_books` → `book_store.py:112 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `book_store.py:117 LOWER(author)=LOWER(?)`; test `test_list_and_author_filter` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `server.py:84 _get_book`, `:111 _not_found` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.py:90 _update_book` → `book_store.py:124 update` (partial) |
| R6 | DELETE /books/{id} | ✓ implemented | `server.py:102 _delete_book` → `book_store.py:138 delete` (204) |
| R7 | SQLite / embedded DB | ✓ implemented | `book_store.py:3,74 sqlite3.connect`, CREATE TABLE books |
| R8 | JSON + appropriate status codes | ✓ implemented | `server.py:137 _send_json`; 201/200/204/400/404/405/413 used |
| R9 | Validation: title & author required | ✓ implemented | `book_store.py:30 validate_book`; test asserts 400 + details |
| R10 | GET /health | ✓ implemented | `server.py:39` returns 200 `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup/run/test/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 11 test functions, 0 skipped |

## Build & Test

Build and tests were **not re-run** — stored scores stand in (per skill §2):

```text
scores.json: test_coverage=0.91, defect_rate=1.0, code_quality=0.6667,
             maintainability=0.9069, idiomatic=0.82, token_efficiency=0.0688
```

`defect_rate=1.0` ⇒ build + all tests passed. `test_coverage=0.91` is line
coverage (tests executed). `grep` of `tests/` finds 0 skip/xfail markers, so all
11 tests are effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 478 |
| Files (source, non-artifact) | server.py, book_store.py, tests/test_api.py, README.md, requirements.txt |
| Dependencies | 1 (pytest; runtime is stdlib-only) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage (stored) | 91% |

## Findings

4 info-level items (full list in `findings.jsonl`) — all beyond-spec enhancements
or documented design notes; no defects, no missing requirements:

1. [info] 405 Method Not Allowed with `Allow` header (beyond spec)
2. [info] Request body size guard returns 413 (beyond spec)
3. [info] Create returns `Location` header (correct REST semantics)
4. [info] `?author=` is exact case-insensitive match, not substring (documented)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores
grep -rcE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/test_api.py   # 0 skips
grep -cE "^def test_" tests/test_api.py           # 11 tests
# optional re-verify: pytest -q
```
