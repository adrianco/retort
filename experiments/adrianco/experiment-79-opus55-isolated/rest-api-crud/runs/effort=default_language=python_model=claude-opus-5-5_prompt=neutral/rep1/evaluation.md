# Evaluation: rest-api-crud (effort=default, python, claude-opus-5-5, prompt=neutral) · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 39 passed / 0 failed / 0 skipped (39 effective)
- **Build:** pass — `test_coverage=0.94` from `scores.json` (tests executed; 89% line coverage in the agent's own run)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 0 info)

## Requirements

Denominator is fixed by the pinned `rest-api-crud/REQUIREMENTS.json` (12 requirements). The `neutral` prompt factor adds no additional checkable instructions.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:207 _create_book` → `BookStore.create` `app.py:92`; `test_create_book` passes |
| R2 | GET /books lists all books | ✓ implemented | `app.py:202 _list_books` → `BookStore.list` `app.py:100`; `test_list_books` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `app.py:203-205` parse_qs → `list(author=)` `app.py:103-105`; `test_list_books_filtered_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:214 _get_book`; `test_get_book`, `test_get_unknown_book` (404) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:220 _update_book` → `BookStore.update` `app.py:115`; `test_update_book`, `test_update_unknown_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:229 _delete_book` → `BookStore.delete` `app.py:125`; `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore` uses `sqlite3` `app.py:66-134`; `test_books_persist_across_restarts` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `_send_json` `app.py:272`; 201/200/204/400/404/405/413 across handlers and tests |
| R9 | Input validation: title and author required | ✓ implemented | `validate_book` `app.py:37-46`; `test_create_rejects_invalid_fields` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:173-176`; `test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Run/Test sections and API table |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 25 test functions, 39 cases, all pass (`test_coverage=0.94`) |

No requirements are partial or missing.

**Enhancements beyond spec** (not deductions): 405 with `Allow` header; 413 for >1 MB bodies; per-field validation `details`; case-insensitive whole-name author match; `Location` header on create; SQL-injection-as-data test; in-memory store test. These are documented in the README's "behaviours the task left open" notes.

## Build & Test

Scores read from `scores.json` (inline gate output); build/test/lint were not re-run per the evaluate-run contract.

```text
scores.json
{"code_quality": 0.789, "token_efficiency": 0.066, "test_coverage": 0.94,
 "defect_rate": 1.0, "maintainability": 1.0, "idiomatic": 0.83}
```

```text
pytest (from the agent's own run, _agent_stdout.log)
app.py   216 stmts, 24 miss, 89% coverage
39 passed in 18.83s
```

`defect_rate=1.0` and `test_coverage=0.94` confirm the build+test gate passed.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 256 |
| Lines of code (test_app.py, non-blank) | 216 |
| Files (project, excl. harness artifacts) | 5 |
| Runtime dependencies | 0 (stdlib only) |
| Dev dependencies | 1 (`pytest`) |
| Tests total | 39 |
| Tests effective | 39 |
| Skip ratio | 0% |

## Findings

None. `findings.jsonl` is empty — the run implements the full spec, all tests execute and pass, and no skipped/disabled tests, build failures, or lint gates were found.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=default_language=python_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                                    # stored mechanical scores (build+test+lint)
cat ../../../REQUIREMENTS.json                      # pinned 12-requirement checklist
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py"   # -> 0 skips
# Optional re-run of tests (not required; scores already stored):
#   python3 -m venv venv && venv/bin/pip install -r requirements-dev.txt && venv/bin/python -m pytest
```
