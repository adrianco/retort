# Evaluation: rest-api-crud · effort=medium language=python model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all passed / 0 failed / 0 skipped (18 test functions, several parametrized; 30 effective cases)
- **Build:** pass (import + tests ran) — from `defect_rate=1.0`, `test_coverage=0.94` in `scores.json`
- **Lint:** pass — `code_quality=0.7889` in `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:180-181` route → `BookStore.create` (`app.py:97-103`); `test_app.py:70 test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:177-179` → `BookStore.list` (`app.py:105-112`); `test_app.py:127 test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:178` parses `author`; `BookStore.list` WHERE `author = ? COLLATE NOCASE` (`app.py:108-109`); `test_app.py:136 test_list_books_filtered_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:187-197` → `BookStore.get`; 404 path `app.py:195-196`; `test_app.py:113,120` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:189-190` → `BookStore.update` (`app.py:122-128`); `test_app.py:152 test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:191-193` → `BookStore.delete`; 204 response; `test_app.py:176 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3` `BookStore` (`app.py:84-133`); `test_app.py:219 test_data_persists_across_store_instances` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `_send` sets JSON content-type (`app.py:228-237`); 201/200/204/400/404/405/413; many tests |
| R9 | Validation: title and author required | ✓ implemented | `validate_book` (`app.py:56-63`); `test_app.py:98 test_create_book_validation` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:171-173` returns `{"status":"ok"}`; `test_app.py:63 test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 18 test functions in `test_app.py`; tests ran (`test_coverage=0.94`) |

No enhancements-beyond-spec are deductions; notable extras: 413 oversized-body guard, 405 `Allow` header, SQL-injection test, malformed-JSON handling.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output) per the evaluate-run skill.

```text
scores.json: {"code_quality": 0.7889, "token_efficiency": 0.0456,
              "test_coverage": 0.94, "defect_rate": 1.0,
              "maintainability": 1.0, "idiomatic": 0.55}
```

`test_coverage=0.94` and `defect_rate=1.0` ⇒ the suite built, imported, and passed
(94% line coverage). No skipped/xfail markers found in `test_app.py`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 484 (app.py 263, test_app.py 221) |
| Files (source) | 4 (app.py, test_app.py, README.md, requirements-dev.txt) |
| Dependencies | 1 dev-only (`pytest`); runtime = stdlib only |
| Tests total | 18 functions (~30 cases with parametrize) |
| Tests effective | ~30 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 94% (`test_coverage`) |

## Findings

Top items (full list in `findings.jsonl`) — none at or above `low`:

1. [info] year accepts any integer (no plausibility range) — beyond spec
2. [info] Stdlib-only `http.server` rather than a framework (idiomatic=0.55)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=medium_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                 # mechanical scores (do not re-run the toolchain)
python -m pytest                # (fallback only) integration tests on an ephemeral port
```
