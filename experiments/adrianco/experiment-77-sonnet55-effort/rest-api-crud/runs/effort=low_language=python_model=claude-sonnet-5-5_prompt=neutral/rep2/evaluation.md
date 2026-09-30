# Evaluation: effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — stdlib only, no build step (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79, idiomatic=0.78 (from scores.json; no lint findings)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate) — not re-run: `test_coverage=0.94`, `defect_rate=1.0`, `code_quality=0.789`, `maintainability=0.886`, `idiomatic=0.78`, `token_efficiency=0.026`.

The prompt factor is `neutral` (`prompts/neutral.md`): it prescribes no methodology and adds no checkable instructions, so there are no `P*` requirements — TASK.md / REQUIREMENTS.json is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `app.py:122-127` POST branch → `BookStore.create` `app.py:29-36`; `test_app.py:36` |
| R2 | GET /books lists all | ✓ implemented | `app.py:119-121` → `BookStore.list` `app.py:38-44`; `test_app.py:48` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:120` parse_qs author → `BookStore.list(author)` `app.py:40-41`; `test_app.py:52` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `app.py:130-131,144-146`; `test_app.py:39,63` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:132-137` → `BookStore.update` `app.py:50-59`; `test_app.py:58` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:138-141` → `BookStore.delete` `app.py:61-65`; `test_app.py:62` |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3.connect` + `CREATE TABLE books` `app.py:15-22`; `__main__` uses `books.db` `app.py:167` |
| R8 | JSON responses + correct status codes | ✓ implemented | `_send` sets `Content-Type: application/json` `app.py:97-103`; 201/200/204/400/404/405 across `_route` |
| R9 | Validation: title & author required | ✓ implemented | `validate()` `app.py:68-86` rejects missing/blank title/author; `test_app.py:42-45` |
| R10 | GET /health | ✓ implemented | `app.py:116-117` returns `{"status":"ok"}`; `test_app.py:32` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md:1-18` (Run / Endpoints / Test) |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` has 5 tests; `test_coverage=0.94 > 0` |

## Build & Test

Not re-run — mechanical scores were computed by the inline eval gate and read from `scores.json`:

```text
test_coverage = 0.94   (build imported + all 5 tests passed)
defect_rate   = 1.0    (build + test succeeded)
```

Test inventory (`test_app.py`): `test_health`, `test_create_and_get`, `test_validation`, `test_list_filter`, `test_update_delete_and_404`. 0 skips/xfails (grep clean).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 234 (app.py 170, test_app.py 64) |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 0 runtime (stdlib); pytest for tests |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (no build step) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [info] Coverage 0.94 (<1.0): `__main__` block and some 405/404 fallback branches unexercised.
2. [info] PUT is full-replace (requires title+author like create); no PATCH-style partial update.

No critical/high/medium/low findings — the run fully implements the spec and all tests pass.

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral/rep2
cat scores.json                          # mechanical scores (not re-run)
grep -cE "^def test_" test_app.py        # 5 tests
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
python -m pytest                         # optional: re-run tests (stdlib + pytest)
```
