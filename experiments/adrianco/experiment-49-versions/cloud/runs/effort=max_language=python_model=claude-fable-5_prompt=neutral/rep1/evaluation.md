# Evaluation: effort=max · language=python · model=claude-fable-5 · prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective) — 19 test functions, one parametrized ×2
- **Build:** pass — `test_coverage=0.99`, `defect_rate=1.0` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.833`, `idiomatic=0.89`, `maintainability=0.861` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a book | ✓ implemented | `app.py:106-126` create_book; `test_app.py:48` test_create_book_returns_201_and_persists |
| R2 | GET /books lists all | ✓ implemented | `app.py:128-140` list_books; `test_app.py:107` test_list_books_returns_all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:130-135` COLLATE NOCASE; `test_app.py:117` test_list_books_filters_by_author |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:142-147` get_book; `test_app.py:132` test_get_missing_book_returns_404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:149-166` update_book; `test_app.py:141` test_put_replaces_book |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:168-175` delete_book; `test_app.py:170` test_delete_book_then_it_is_gone |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:11-37` sqlite3 schema + connection; `test_app.py:203` test_data_persists_across_app_instances |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/400/204/405 across `app.py`; `test_app.py:188-197` JSON 404/405 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:38-45` REQUIRED_FIELDS; `test_app.py:70` test_create_book_requires_title_and_author |
| R10 | GET /health | ✓ implemented | `app.py:101-104` health (also pings DB); `test_app.py:39` test_health |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, tests, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 20 effective tests; `test_coverage=0.99` |

Prompt factor `neutral` prescribes no methodology and adds no checkable instructions (P* list empty).

## Build & Test

Not re-run — stored scores used per skill (mechanical scorers already executed the toolchain):

```text
scores.json: test_coverage=0.99  defect_rate=1.0  code_quality=0.833
             maintainability=0.861  idiomatic=0.89  token_efficiency=0.0123
```

`test_coverage=0.99` ⇒ build succeeded and effectively all tests pass; `defect_rate=1.0`
confirms build+test success. `.coverage` artifact present in the archive.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 440 (app.py 187, db.py 44, test_app.py 209) |
| Files | 13 (incl. artifacts); 3 source + 1 test + README + requirements |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 20 (19 functions, 1 parametrized ×2) |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build/test | pass (from scores.json) |

## Findings

Top items (full list in `findings.jsonl` — all info-level, no defects):

1. [info] Framework errors returned as JSON via a global HTTPException handler (`app.py:177-181`)
2. [info] Unknown-field rejection and strict type validation beyond required title/author (`app.py:34-61`)
3. [info] Persistence verified across separate app instances (`test_app.py:203-209`)

No requirement gaps, no failing or skipped tests, no build/lint failures.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=max_language=python_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                      # stored mechanical scores (no re-run)
grep -cE "^def test_" test_app.py    # 19 test functions
grep -rE "pytest\.skip|xfail" test_app.py | wc -l   # 0 skips
# optional live check:
python3 -m pytest -v
```
