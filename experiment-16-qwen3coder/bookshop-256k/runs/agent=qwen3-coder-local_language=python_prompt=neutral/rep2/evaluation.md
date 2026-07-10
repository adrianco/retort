# Evaluation: agent=qwen3-coder-local language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, prompt=neutral, framework=flask (inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — `defect_rate=1.0` from scores.json confirms build+tests passed; coverage `test_coverage=0.76`
- **Build:** pass (import/collection succeeded — `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.833` from scores.json; no blocking warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

Scores read from `scores.json` (inline gate) — build/tests/lint NOT re-run:
`test_coverage=0.76`, `code_quality=0.833`, `defect_rate=1.0`, `maintainability=0.911`, `idiomatic=0.73`, `token_efficiency=0.0108`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:48-70 create_book`; test `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:73-82 get_books`; test `test_get_all_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:75-80` filter_by(author); test `test_get_books_by_author` |
| R4 | GET /books/{id} returns a single book (404 if absent) | ✓ implemented | `app.py:85-88` get_or_404; tests `test_get_single_book`, `test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:91-114 update_book`; tests `test_update_book`, `test_update_nonexistent_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:117-127 delete_book`; tests `test_delete_book`, `test_delete_nonexistent_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:11` sqlite:///books.db; `books.db` present in workspace |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | jsonify + 201/200/400/404/500 throughout `app.py` |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:53`; test `test_create_book_missing_fields` (400) |
| R10 | GET /health health-check | ✓ implemented | `app.py:43-45 health_check`; test `test_health_check` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:22-34` Setup + Run sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 11 test methods; `test_coverage=0.76 > 0` |

Prompt factor = `neutral` (prompts/neutral.md prescribes no methodology and adds no checkable requirements) → no `P*` requirements.

## Build & Test

Not re-run — scores read from `scores.json` (inline eval gate). Signals:

```text
defect_rate = 1.0     # build + tests succeeded
test_coverage = 0.76  # line coverage; tests executed and passed
code_quality = 0.833  # lint/quality
```

Test inventory (static): 11 `def test_*` methods in `test_app.py`, 0 skips
(`grep -Ec "unittest.skip|pytest.skip|xfail|skipTest"` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + demo.py) | 196 |
| Files (non-artifact) | 10 |
| Dependencies | 2 (Flask, Flask-SQLAlchemy) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage (test_coverage) | 0.76 |

## Findings

Top items (full list in `findings.jsonl` — 0 critical/high/medium):

1. [low] Q1 — PUT /books/{id} does not re-validate that title/author stay non-empty (`app.py:100-107`)
2. [low] Q2 — Tests run against the app's real `books.db` rather than an isolated/in-memory DB (`test_app.py:6-11`)
3. [info] Q3 — Write handlers catch bare `Exception` and return generic 500 (`app.py:68,112,125`)
4. [info] E1 — Adds created_at/updated_at timestamps and a `demo.py` driver beyond spec

## Reproduce

```bash
cd "experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=python_prompt=neutral/rep2"
cat scores.json                              # stored mechanical scores (not re-run)
grep -Ec "unittest.skip|pytest.skip|xfail|skipTest" *.py   # skip count -> 0
grep -c "def test_" test_app.py              # test count -> 11
# Optional full re-run (not required; scores already stored):
# pip install -r requirements.txt && python -m pytest test_app.py
```
