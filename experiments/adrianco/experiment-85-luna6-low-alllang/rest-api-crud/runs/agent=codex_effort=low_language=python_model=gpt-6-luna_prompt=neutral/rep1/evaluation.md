# Evaluation: agent=codex effort=low language=python model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (import succeeds) — from `test_coverage=0.68` in `scores.json`
- **Lint:** pass — `code_quality=0.62`, `idiomatic=0.60` (mechanical, from `scores.json`); 1 low-severity warning
- **Architecture:** `run-summary` skill unavailable — summarised inline below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

The neutral prompt factor (`prompts/neutral.md`) prescribes no methodology and adds no
checkable instructions, so there are no `P*` requirements; TASK.md / `REQUIREMENTS.json`
is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:115-119` POST route → `BookStore.create` (`app.py:63-70`) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:112-114` → `BookStore.list` (`app.py:47-56`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:113` `parse_qs(...).get("author")`; `app.py:52-55` SQL filter; test `test_app.py:34` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:123-125`; 404 path `app.py:125`; test `test_app.py:48` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:126-131` → `BookStore.update` (`app.py:72-81`); test `test_app.py:35-39` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:132-135` → `BookStore.delete` (`app.py:83-86`); test `test_app.py:41` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:26-41` `sqlite3.connect` + `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:141-149` `_send` JSON; `HTTPStatus` 200/201/204/400/404 throughout |
| R9 | Validation: title and author required | ✓ implemented | `validate_book` `app.py:89-103`; 400 on missing/blank; tests `test_app.py:46-47` |
| R10 | GET /health health check | ✓ implemented | `app.py:110-111` → `{"status": "ok"}`; test `test_app.py:21` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run, API, Tests sections |
| R12 | At least 3 tests | ✓ implemented | `tests/test_app.py` 3 `def test_*`; `test_coverage=0.68` (ran) |

## Build & Test

Not re-run — scores read from `scores.json` (skill step 2):

```text
test_coverage = 0.68   # tests executed; 68% coverage (>0 ⇒ build/import + tests ran)
defect_rate   = 0.9134 # build + test succeeded
code_quality  = 0.6222
maintainability = 0.7938
idiomatic     = 0.60
token_efficiency = 0.0173
```

3 tests defined, 0 skipped (`grep` for `pytest.skip|@pytest.mark.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 227 |
| Lines of code (tests) | 49 |
| Source files | 3 (app.py, tests/test_app.py, README.md) |
| Dependencies | 0 (stdlib only; no requirements.txt/pyproject.toml) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] Redundant `log_message` override is a no-op — `app.py:202-204`
2. [info] Dependency-free stdlib implementation (no web framework) — `app.py:6-12`

No requirement gaps, no build/test failures, no skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (not re-run)
grep -rE "def test_" tests/ --include="*.py" | wc -l
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
# to actually run tests (not required here): python -m pytest
```
