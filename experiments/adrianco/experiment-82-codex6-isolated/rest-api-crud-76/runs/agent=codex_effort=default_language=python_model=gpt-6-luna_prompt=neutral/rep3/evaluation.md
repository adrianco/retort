# Evaluation: rest-api-crud · agent=codex model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=codex, model=gpt-6-luna, prompt=neutral, effort=default, framework=unknown (stdlib)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `retort.db`/`scores.json` (`defect_rate=1.0`, `test_coverage=0.88`)
- **Lint:** pass — `code_quality=0.7889` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:85-96` INSERT + 201; `test_app.py:39` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:77-84` SELECT all |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:78-83` nullable WHERE; `test_app.py:47-48` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:108-109` + `app.py:106-107` 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:110-121` UPDATE + reselect; `test_app.py:49-51` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:122-125` DELETE + 204; `test_app.py:56-58` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18-30` `sqlite3.connect` + CREATE TABLE |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `_response` `app.py:33-37`; 201/200/404/400/204/405 |
| R9 | Validation: title and author required | ✓ implemented | `_validate` `app.py:49-60`; `test_app.py:55` (400) |
| R10 | GET /health health-check | ✓ implemented | `app.py:67-68` returns `{status: ok}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` (run, endpoints, test) |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 test functions; `test_coverage=0.88 > 0` |

## Build & Test

Scores read from the archive (not re-run, per skill step 2):

```text
scores.json: {"code_quality": 0.7889, "token_efficiency": 0.0212,
              "test_coverage": 0.88, "defect_rate": 1.0,
              "maintainability": 0.8807, "idiomatic": 0.68}
```

`defect_rate=1.0` ⇒ build + tests succeeded. `test_coverage=0.88` is the coverage
fraction (tests executed and passed). No skipped/xfail markers found in `test_app.py`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 134 (app.py) + 58 (test_app.py) = 192 |
| Files (source, excl. artifacts/logs) | 4 (app.py, test_app.py, README.md, stack.json) |
| Dependencies | 0 (Python standard library only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build/test | pass (`defect_rate=1.0`) |

## Findings

None. All 12 pinned requirements implemented, tests pass, no skipped/disabled
tests, no build/lint failures at or above tracked severity.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                     # stored mechanical scores (not re-run)
cat ../../REQUIREMENTS.json         # pinned requirement checklist
grep -nE '^def test_' test_app.py   # 3 tests, 0 skips
# to re-run tests locally (optional): python -m pytest
```
