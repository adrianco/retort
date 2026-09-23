# Evaluation: effort=max language=python model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, effort=max, prompt=neutral (agent/framework unknown in stack.json)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 63 test functions / 0 failed / 0 skipped (63 effective) — `test_coverage=0.99`
- **Build:** pass — `defect_rate=1.0` (build + tests succeeded), from `scores.json`
- **Lint:** pass — `code_quality=0.83` from `scores.json` (no separate lint re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

Scores read from `scores.json` (inline gate output): test_coverage=0.99,
defect_rate=1.0, code_quality=0.833, maintainability=0.904, idiomatic=0.87.
Build/test/lint were **not** re-run per the evaluate-run contract.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `books_api/app.py:87` create_book → `db.py:119` create; test `test_api.py:69` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:99` list_books → `db.py:135`; test `test_api.py:195` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.py:142` instr(fold(author),?); tests `test_api.py:210,222,232,239` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:108` get_book; tests `test_api.py:253,261,276` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:116` replace_book → `db.py:148` replace; test `test_api.py:284` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:129` delete_book → `db.py:158`; test `test_api.py:344` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:10` sqlite3, `_SCHEMA` books table; test `test_api.py:461` survives restart |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/204/400/404/405/413/415/503 throughout `app.py`/`errors.py`; test `test_api.py:69,437` |
| R9 | Validation: title and author required | ✓ implemented | `schemas.py:63` RequiredText min_length=1, trimmed; tests `test_api.py:147,151` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:77` health; tests `test_api.py:33,39` |
| R11 | README.md with setup + run instructions | ✓ implemented | `README.md` (150 lines): Setup, Run, endpoint table, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 63 test functions, 0 skips; `test_coverage=0.99` |

No prompt-factor requirements (`prompt=neutral` is a tone/style factor with no
additional checkable instructions beyond TASK.md).

## Build & Test

Not re-run — scores taken from `scores.json` written by the inline scoring gate:

```text
scores.json: test_coverage=0.99  defect_rate=1.0  code_quality=0.833
             maintainability=0.904  idiomatic=0.87
```

`defect_rate=1.0` ⇒ build + full test suite passed. `test_coverage=0.99` ⇒
tests executed and nearly all lines covered. Skip scan (`grep pytest.skip|xfail`
over `tests/`) returned 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, books_api/) | 637 |
| Lines of code (tests/) | 778 |
| Files (non-artifact) | 21 |
| Runtime dependencies | 4 (fastapi, pydantic, starlette, uvicorn) |
| Tests total | 63 |
| Tests effective | 63 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — all beyond-spec enhancements,
no defects:

1. [info] E1 — RFC 9457 problem-details errors across all failure modes
2. [info] E2 — Request body size-limit ASGI middleware (413)
3. [info] E3 — Unicode-aware case-insensitive author filter
4. [info] E4 — Health endpoint verifies DB readability, not just liveness
5. [info] E5 — 63-test suite with zero skips

## Reproduce

```bash
cd "experiments/adrianco/experiment-74-opus55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                        # stored build/test/lint scores
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ | wc -l   # = 0
grep -rE "def test_" tests/*.py | wc -l                # = 63
# (build/tests deliberately NOT re-run — see evaluate-run step 2)
```
