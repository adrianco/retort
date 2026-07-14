# Evaluation: agent=hermes-local language=python prompt=none stack=s2 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask (inferred), prompt=none, stack=s2
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 24 defined / 0 skipped (24 effective); test_coverage=0.96 ⇒ build + tests pass
- **Build:** pass — from scores.json (test_coverage=0.96, defect_rate=1.0); not re-run
- **Lint:** pass — code_quality=0.79 from scores.json; not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:85-120` create_book, INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:122-136` list_books |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:128-132` LIKE filter; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `app.py:138-147`, 404 at :145 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:149-182`, UPDATE + reselect |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:184-196`, DELETE + 404 handling |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:7,44-72` sqlite3, file-based books.db |
| R8 | JSON responses with appropriate status codes | ✓ implemented | jsonify throughout; 201/200/400/404 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:96-100`; tests `test_create_book_missing_title/author` |
| R10 | GET /health health check | ✓ implemented | `app.py:80-83` returns `{status: healthy}` 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` setup, run, API examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 24 test functions in `test_app.py`; test_coverage=0.96 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json: {"code_quality": 0.789, "token_efficiency": 0.0096,
              "test_coverage": 0.96, "defect_rate": 1.0,
              "maintainability": 1.0, "idiomatic": 0.7}
```

```text
test_coverage=0.96 ⇒ build succeeded and all tests passed (test gate).
defect_rate=1.0 ⇒ build+test succeeded.
Agent stdout log reports "Test results: 24/24 passed".
Skip scan (pytest.skip / @pytest.mark.skip / xfail): 0 matches.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app.py+test_app.py) | ~586 |
| Files (excl. __pycache__) | 14 (incl. archive/meta files) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 24 |
| Tests effective | 24 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] No pagination on GET /books — `app.py:122-136`
2. [low] No format validation for year/isbn — `app.py:102-103`
3. [info] Author filter uses substring LIKE match — `app.py:129-132`
4. [info] Committed books.db build artifact in archive

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s2/rep3
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # skip scan → 0
grep -cE "def test_" test_app.py                  # test count → 24
# To re-verify tests locally (not required; scores already stored):
pip install flask pytest && pytest test_app.py -v
```
