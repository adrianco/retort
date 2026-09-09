# Evaluation: agent=codex effort=low language=python model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok — `experiment_runs.id=1` is `completed`. Note this is the **repair** attempt (`_second_try=1.0`); the first attempt is archived beside it as `rep1-failed`, and `TASK.md`/`FEEDBACK.md` in this workspace are the repair prompt, not the original task.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 9 test methods, 0 skipped (9 effective). All pass — `defect_rate=1.0`, `test_coverage=0.99`.
- **Build:** pass — `test_coverage=0.99` from `scores.json` (≠ 0 ⇒ the module imported and the suite executed); `defect_rate=1.0` ⇒ build+test succeeded.
- **Lint:** unavailable — `ruff` is not installed on this machine, so the lint term of `code_quality` was the neutral 0.5 placeholder, not a measurement (see finding F1). 0 observed lint warnings.
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist taken verbatim from the pinned `REQUIREMENTS.json` (`rest-api-crud`, 12 entries) — no per-run extraction.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:79-89 create_book` — INSERT of all four columns, 201 + `Location`; `test_app.py:20-24` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:91-99 list_books` — `SELECT * FROM books ORDER BY id`; `test_app.py:25` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:93,97-98` — parameterised `WHERE author = ?`; `test_app.py:34-40` (incl. an injection assertion) |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `app.py:101-106 get_book`; 404 path at `app.py:104-105`; `test_app.py:31,59-63` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:108-119 update_book` — full replace, 404 on `rowcount==0`; `test_app.py:26-29` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:121-129 delete_book` — 404 on `rowcount==0`; `test_app.py:30-32` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4,21` `sqlite3.connect`, DDL at `app.py:33-41`; persistence proved across a fresh `create_app` at `test_app.py:76-78` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `app.py:87`, 200 `app.py:99/106/119/129`, 404 `app.py:105/112/118/124/128`, 400 `app.py:67`, plus `HTTPException`→JSON at `app.py:43-45` (covers 404/405/415); asserted at `test_app.py:59-71` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:47-63 validated_book` — non-blank `str` check on both, `ValueError`→400 at `app.py:65-67`; `test_app.py:42-51` covers `{}`, `[]`, `null`, title-only, whitespace title, non-string author |
| R10 | GET /health | ✓ implemented | `app.py:74-77 health` — `SELECT 1` probe then `{"status":"ok"}`; `test_app.py:74-75` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — venv + `pip install -r requirements.txt` + `python app.py`, endpoint table, error contract, test commands |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 methods in `test_app.py:19-103`; suite executed (`test_coverage=0.99`) |

Prompt-factor requirements (`prompts/neutral.md`): the neutral level prescribes no methodology and only asks for "tests that demonstrate the implementation meets the requirements" — satisfied by the 9 tests above. No additional checkable `P*` instructions.

**Enhancements beyond spec** (not deductions, recorded for cross-run comparison): signed-64-bit range validation on `year` and on path ids (`app.py:9-10,54-59,70,111,123`), strict `type(x) is int` so `True` is rejected as a year, a SQL-injection assertion in the filter test (`test_app.py:40`), an invalid-update-preserves-state test (`test_app.py:53-57`), and a boundary test at exactly ±2^63 (`test_app.py:91-95`).

## Build & Test

Per the skill, the toolchain was **not** re-run — the scores retort already computed for this run were read from `scores.json`, and cross-checked against `run_results` for `experiment_runs.id=1`:

```text
$ cat scores.json
{"code_quality": 0.7888888888888889, "token_efficiency": 0.02845421771620371,
 "test_coverage": 0.99, "defect_rate": 1.0, "maintainability": 1.0, "idiomatic": 0.84}

$ sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=1;"
code_quality|0.788888888888889
test_coverage|0.99
defect_rate|1.0
maintainability|1.0
idiomatic|0.84
_duration_seconds|60.7926774583757
_tokens|144794.0
_second_try|1.0
_cost_usd|0.413308
_agent_steps|9.0
```

`test_coverage=0.99` (not 0) ⇒ the suite built, imported and ran; `defect_rate=1.0` ⇒ build+test succeeded. The missing 1% is only the two `__main__` guards — decoded from the run's own `.coverage` bitmap, the *only* uncovered statements in the workspace are `app.py:135 create_app().run(...)` and `test_app.py:107 unittest.main()`. Every other statement in both files is covered.

Lint (`ruff check --select E,F,W`) never executed: `ruff` is absent from PATH and from any venv in the workspace, so `CodeQualityScorer._lint_score` returned its `FileNotFoundError` neutral 0.5. The recorded `code_quality` reconstructs exactly as `(0.5 + 0.8667 + 1.0)/3 = 0.78889`, where 0.8667 is the structure term for 2 source files (`min(1, 2/3) + 0.2` test bonus) and 1.0 is the clean-stderr term. So the 0.79 is a two-flat-files structure penalty plus a missing linter — **not** evidence of lint defects.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 242 (`app.py` 135 + `test_app.py` 107) |
| Source files | 2 (`.py`) |
| Files in workspace (excl. `__pycache__`) | 15 (incl. retort's own `TASK.md`, `FEEDBACK.md`, `_meta.json`, logs) |
| Dependencies | 1 (`Flask>=2.3,<4`) |
| Tests total | 9 methods (several with `subTest` fan-out) |
| Tests effective | 9 |
| Skip ratio | 0% (0 matches for `skip`/`xfail`/`skipTest` across `*.py`) |
| Line coverage | 99% (only the two `__main__` guards uncovered) |
| Agent wall-clock | 60.79 s |
| Agent steps / tokens / cost | 9 / 144,794 / $0.4133 |

## Findings

Full list in [`findings.jsonl`](findings.jsonl). No critical, high or medium findings.

1. `[low] F2` — `create_book` dereferences `find_book()` without a `None` guard (`app.py:86`): a concurrent DELETE between the committed INSERT and the re-SELECT turns a successful create into a 500.
2. `[info] F1` — lint was never actually run (`ruff` not installed); `code_quality`'s lint term is a neutral placeholder, so 0.79 understates this code.
3. `[info] F3` — defensive behaviour beyond the spec (64-bit range guards, strict int typing, injection and persistence assertions).

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep1"

cat scores.json                    # stored mechanical scores — do NOT re-run the toolchain
sqlite3 -readonly ../../../retort.db \
  "SELECT metric_name,value FROM run_results WHERE run_id=1;"

grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail|@unittest\.skip|self\.skipTest" . --include="*.py" | wc -l
grep -cE "^\s+def test_" test_app.py
wc -l app.py test_app.py
which ruff || echo "ruff NOT on PATH"    # why the lint term is 0.5
```
