# Evaluation: rest-api-crud (effort=max, python, claude-haiku-5-5, prompt=neutral) · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 29 methods / 0 failed / 0 skipped (29 effective) — passed per `defect_rate=1.0`, `test_coverage=0.94` (from `scores.json`)
- **Build:** pass — stored (`defect_rate=1.0`; no re-run)
- **Lint:** pass with warnings — `code_quality=0.6667` (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.py:123 _create_book` → `store.py:43 create`; test `test_create_returns_201_with_location_and_stored_book` |
| R2 | GET /books lists all books | ✓ implemented | `server.py:119 _list_books` → `store.py:63 list_books`; test `test_list_books_and_filter_by_author` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.py:120`, `store.py:70-72` (casefold match); tests `test_author_filter_is_case_insensitive*`, `*_folds_non_ascii_case` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.py:128 _get_book` raises 404; test `test_get_book_by_id_and_unknown_ids` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.py:134 _update_book` → `store.py:78 update`; test `test_put_updates_supplied_fields_and_clears_on_null` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.py:141 _delete_book` → `store.py:91 delete`; test `test_delete_removes_the_book` |
| R7 | Data stored in SQLite | ✓ implemented | `store.py:3,38 sqlite3.connect` + SCHEMA; test `test_data_survives_reopening_the_database_file` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `server.py:166 _send` JSON; 201/200/204/400/404/405/413/415/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `validation.py:47-56`; tests `test_create_requires_title_and_author`, `test_create_reports_each_missing_required_field` |
| R10 | GET /health health check | ✓ implemented | `server.py:111 _health` (pings DB, 200/503); test `test_health_reports_ok` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run, Test, API, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 29 test methods in `test_books_api.py`; `test_coverage=0.94` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 0.94   # tests executed and passed; 94% line coverage
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.6667 # lint/quality signal (warnings)
maintainability = 0.914
idiomatic     = 0.92
```

Skip scan: `grep -rE "skip|xfail"` over `*.py` → 0 matches. No skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. tests) | 723 (server 221, store 102, validation 111, tests 289) |
| Files (source + README) | 5 |
| Dependencies | 0 (Python standard library only) |
| Tests total | 29 |
| Tests effective | 29 |
| Skip ratio | 0% |
| Build/test | pass (`defect_rate=1.0`) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] code_quality score 0.67 despite clean, documented code — likely module-length/complexity lint thresholds; no functional impact
2. [info] Thread-safe SQLite store beyond spec (`store.py:36-41`)
3. [info] Extra HTTP edge-case handling: 413/415/405/overflow-id guard
4. [info] Unicode-aware case-insensitive author filter (`store.py:18-21`)

No missing, partial, failing, or skipped requirements. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -rEn "skip|xfail" *.py | wc -l               # 0 skips
wc -l server.py store.py validation.py test_books_api.py
# optional re-run of tests (skill says prefer stored scores):
# python -m unittest -v
```
