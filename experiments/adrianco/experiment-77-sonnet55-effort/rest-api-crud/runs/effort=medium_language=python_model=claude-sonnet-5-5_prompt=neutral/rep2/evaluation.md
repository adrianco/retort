# Evaluation: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, effort=medium, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — `test_coverage=0.97` from scores.json
- **Build:** pass — from `test_coverage=0.97` (tests executed; not re-run)
- **Lint:** pass — `code_quality=0.79` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (constant 12-item denominator, used verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:62-68` INSERT then re-select → 201; `test_app.py:36` test_create_and_get |
| R2 | GET /books lists all books | ✓ implemented | `app.py:74-76` SELECT * ORDER BY id; `test_app.py:50` test_list_and_author_filter |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:70-73` filters by `author` query param; `test_app.py:54-56` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `app.py:81-82` + `get_book` raises 404 `app.py:52-56`; `test_app.py:39`, `test_app.py:70` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:83-90` (full replace); `test_app.py:59` test_update (200/400/404) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:91-95` → 204; `test_app.py:67` test_delete |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17-27` `sqlite3.connect` + CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:114-119` JSON body + status phrase map (200/201/204/400/404/405) |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:30-46` `validate()` rejects empty title/author → 400; `test_app.py:42` test_validation |
| R10 | GET /health health check | ✓ implemented | `app.py:59-60` returns `{"status":"ok"}`; `test_app.py:32` test_health |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md:6-11` Run section, `README.md:33-36` Tests section |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 7 `test_*` functions in `test_app.py`; `test_coverage=0.97` (> 0) |

No `prompt`-factor requirements: `prompt=neutral` maps to a task-neutral instruction, no additional checkable `P*` items.

## Build & Test

Not re-run — stored scores used per skill (scores.json present, computed inline during `retort run`):

```text
scores.json: test_coverage=0.97  defect_rate=1.0  code_quality=0.7888..  maintainability=0.985  idiomatic=0.68
test_coverage=0.97 ⇒ build succeeded and tests executed & passed
defect_rate=1.0    ⇒ build+test succeeded
```

Skip scan (test_app.py): 0 matches for `pytest.skip` / `@pytest.mark.skip` / `xfail` — no skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 203 (app.py 127 + test_app.py 76) |
| Files (source/docs) | 4 (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 0 (stdlib only; no requirements.txt/pyproject.toml) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (all info; full list in `findings.jsonl`):

1. [info] Dependency-free stdlib implementation (WSGI + sqlite3) — `app.py:1-6`
2. [info] Validation & error handling beyond spec (405, typed year/isbn, malformed JSON) — `app.py:38-43,96,104`
3. [info] PUT /books/{id} is a full replace (all fields required), not partial — acceptable per R5 — `app.py:83-90`

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat scores.json                          # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json           # pinned 12-item checklist
grep -cE "^def test_" test_app.py        # 7 tests
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
```
