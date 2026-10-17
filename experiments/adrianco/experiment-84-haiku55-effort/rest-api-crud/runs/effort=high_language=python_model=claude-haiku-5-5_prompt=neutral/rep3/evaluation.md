# Evaluation: effort=high language=python model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 46 passed / 0 failed / 0 skipped (46 effective) — scores from retort
- **Build:** pass — defect_rate=1.0 (from `scores.json`)
- **Lint:** pass — code_quality=0.67 (from `scores.json`), no failing gate
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:_create_book` → `store.py:create_book`; `test_create_book_returns_201_with_location_and_body` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:_list_books` → `store.py:list_books`; `test_list_returns_all_books_in_id_order` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.py:list_books` `WHERE author COLLATE NOCASE = ?`; `test_list_filters_by_author_case_insensitively` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:_get_book`; `test_get_book_by_id`, `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:_update_book` → `store.py:update_book`; `test_put_replaces_book`, `test_put_missing_book_returns_404` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:_delete_book` → `store.py:delete_book`; `test_delete_book_then_it_is_gone` |
| R7 | Data stored in SQLite | ✓ implemented | `store.py:BookStore` uses `sqlite3`, `SCHEMA` CREATE TABLE; `test_data_persists_across_store_instances` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:_json` sets JSON Content-Type; 201/200/204/400/404/405/413/415/500 mapped centrally |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:_required_text`; `test_create_requires_title_and_author` (parametrized) |
| R10 | GET /health health check | ✓ implemented | `app.py:_health` pings DB; `test_health_check_reports_ok`, `..._unavailable_when_database_is_closed` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — Setup, Run, Endpoints, Errors, Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 46 effective tests, `test_coverage=0.95` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage   = 0.95   # build + all tests ran and passed (95% line coverage)
defect_rate     = 1.0    # build + test succeeded
code_quality    = 0.6667 # lint/quality heuristic
maintainability = 0.9181
idiomatic       = 0.8
token_efficiency= 0.0253  # very low — verbose high-effort solution
```

README documents the suite as 46 tests; `grep "def test_"` = 35 functions, +11 from parametrization (2+2+5+4+3 cases) = 46. Zero skips/xfail.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `bookapi/*.py`) | 385 |
| Lines of code (tests) | 421 |
| Files (excl. artifacts) | 16 |
| Dependencies | 1 (pytest, dev-only; stdlib-only runtime) |
| Tests total | 46 |
| Tests effective | 46 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top items by severity (full list in `findings.jsonl`) — all info-level; no conformance defects:

1. [info] code_quality score 0.67 despite clean, passing build — scorer heuristic, not a code defect
2. [info] Edge-case handling well beyond spec (SQLite-overflow id → 404, 415/413 guards, Allow header)
3. [info] 46 tests including real-socket E2E and cross-reopen persistence

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                    # stored build/test/lint scores
cat ../../REQUIREMENTS.json                         # pinned 12-item checklist
grep -rE "pytest\.skip|xfail" tests/ | wc -l        # 0 skips
python -m pytest                                    # optional: 46 passed
```
