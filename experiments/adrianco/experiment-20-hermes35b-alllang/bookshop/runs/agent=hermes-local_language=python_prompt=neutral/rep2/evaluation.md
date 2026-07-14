# Evaluation: agent=hermes-local language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask (inferred), prompt=neutral
- **Status:** ok (functionally complete; one required deliverable — README.md — missing)
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R11 README.md)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — from defect_rate=1.0
- **Build:** pass — from retort.db/scores.json (defect_rate=1.0; not re-run)
- **Lint:** pass — code_quality=0.83 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:44` `create_book_endpoint`, `models.py:66` `create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:69` `list_books_endpoint`, `models.py:111` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:72`, `models.py:121` LOWER(author)=LOWER(?); test `test_app.py:119` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:77`, 404 at `:81`; test `test_app.py:147` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:86`, `models.py:134`; partial-update test `test_app.py:170` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:115`, `models.py:182`; test `test_app.py:191` |
| R7 | SQLite persistence | ✓ implemented | `models.py:48` `CREATE TABLE books`, file-backed `books.db` |
| R8 | JSON + HTTP status codes | ✓ implemented | `jsonify(...), 201/200/400/404` throughout `app.py` |
| R9 | Validate title & author required | ✓ implemented | `app.py:56-59`, `models.py:81-84`; tests `test_app.py:84,92` |
| R10 | GET /health | ✓ implemented | `app.py:38` `health_check`; test `test_app.py:49` |
| R11 | README.md setup/run docs | ✗ missing | no README.md in run_dir |
| R12 | ≥3 unit/integration tests | ✓ implemented | 15 tests in `test_app.py`; test_coverage=0.69 (ran) |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and asks
for tests demonstrating the requirements — satisfied by the 15-test suite. No
additional checkable P-requirements.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (skill Step 2):

```text
scores.json: defect_rate=1.0 (build+tests pass), test_coverage=0.69,
code_quality=0.83, maintainability=0.91, idiomatic=0.70,
token_efficiency=0.0108
```

```text
15 test functions in test_app.py; 0 skips (grep pytest.skip/xfail = 0).
defect_rate=1.0 ⇒ all executed and passed.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 545 (app 128, models 208, tests 209) |
| Files | 13 (incl. artifacts); 3 source .py |
| Dependencies | 2 (flask, pytest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Coverage | 69% (test_coverage) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [high] R11 — No README.md deliverable (required by spec; absent)
2. [low] Q1 — Dead/broken `get_db_path()` in `app.py:15-17`
3. [info] Q2 — Very low token efficiency (0.0108)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep2
cat scores.json                          # mechanical scores (no re-run)
grep -cE "def test_" test_app.py         # 15
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0
ls README.md                             # absent -> R11 missing
```
