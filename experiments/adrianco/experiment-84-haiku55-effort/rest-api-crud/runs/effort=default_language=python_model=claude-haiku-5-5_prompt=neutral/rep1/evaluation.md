# Evaluation: rest-api-crud (effort=default, python, claude-haiku-5-5, prompt=neutral) · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — pass inferred from `test_coverage=0.95`
- **Build:** pass — from `scores.json` (`test_coverage=0.95`, `defect_rate=1.0`); not re-run
- **Lint:** pass — `code_quality=0.6222` from `scores.json`; not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate output): `test_coverage=0.95`, `defect_rate=1.0`,
`code_quality=0.6222`, `maintainability=1.0`, `idiomatic=0.85`, `token_efficiency=0.0220`. Build,
tests, and lint were **not** re-run per the skill (scores already computed during scoring).

A clean, complete stdlib-only implementation: every requirement is satisfied with test evidence
and no defects, skips, or missing deliverables were found. All four findings are beyond-spec
enhancements (info).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `books_api.py:216-219` `_create_book` → `BookStore.create` (:105-112) |
| R2 | GET /books lists all | ✓ implemented | `books_api.py:211-214` `_list_books` → `BookStore.list` (:119-128); test `test_list_books_and_filter_by_author` |
| R3 | GET /books ?author= filter | ✓ implemented | `books_api.py:212` reads `author` query; `:124-127` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} w/ 404 | ✓ implemented | `books_api.py:221-225` `_get_book`; `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `books_api.py:227-232` `_update_book` → `BookStore.update` (:130-141); `test_update_book_partial_and_full` |
| R6 | DELETE /books/{id} | ✓ implemented | `books_api.py:234-237` `_delete_book` → `BookStore.delete` (:143-146); `test_delete_book` |
| R7 | SQLite persistence | ✓ implemented | `books_api.py:89-146` `BookStore` over `sqlite3`; schema `:26-34` |
| R8 | JSON + correct status codes | ✓ implemented | `_send_json`/`_send_error` (:252-259); 201/200/204/400/404/405 across handlers |
| R9 | Validation: title/author required | ✓ implemented | `books_api.py:54-63` `validate_book`; `test_create_requires_title_and_author` |
| R10 | GET /health | ✓ implemented | `books_api.py:181-182` returns `{"status":"ok"}`; `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Test, API sections |
| R12 | ≥3 tests | ✓ implemented | 15 test functions in `test_books_api.py`; `test_coverage=0.95` |

## Build & Test

Not re-run — scores read from `scores.json`:

```text
test_coverage = 0.95   # build + tests executed and passed (coverage 95%)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.6222 # lint/quality
```

Skip scan (`grep pytest.skip|@pytest.mark.skip|xfail`): 0 matches — no skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 502 (books_api.py 306 + test_books_api.py 196) |
| Files (deliverables) | 3 (books_api.py, test_books_api.py, README.md) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are info-level (beyond-spec enhancements); full list in `findings.jsonl`:

1. [info] E1 — 405 + `Allow` header for wrong-method requests
2. [info] E2 — ISBN-10/13 + year validation beyond required title/author checks
3. [info] E3 — PUT applies partial updates (omitted fields preserved)
4. [info] E4 — request body size bounded; malformed-JSON / non-object bodies rejected

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -cE '^def test_' test_books_api.py           # 15 tests
grep -rEc 'pytest\.skip|@pytest\.mark\.skip|xfail' test_books_api.py  # 0 skips
# Optional manual re-run: python -m pytest -v
```
