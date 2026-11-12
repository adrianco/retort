# Evaluation: rest-api-crud · effort=low_language=python_model=claude-fable-5-2_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`, R1–R12)
- **Tests:** passed (13 functions, +7 parametrised cases ≈ 19 cases) / 0 failed / 0 skipped — all effective
- **Build:** pass — `test_coverage=0.92`, `defect_rate=1.0` from `scores.json` (build + full test suite ran and passed)
- **Lint:** pass — `code_quality=0.789` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `{run_dir}/scores.json` (inline gate output); build/test/lint NOT re-run.
Prompt factor = `neutral`, which prescribes no methodology and adds no checkable
instructions, so the P-list is empty — TASK.md / `REQUIREMENTS.json` is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:184-186` validate→`store.create`, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:181-183` → `store.list`; `test_app.py:88` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:182` + `app.py:83` `WHERE author=? COLLATE NOCASE`; `test_app.py:97` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.py:192-204`; 404 at `:203`; `test_app.py:128` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:194-195` → `store.update`; `test_app.py:104` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:196-198` → `store.delete`, 204; `test_app.py:121` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore` `sqlite3.connect` `app.py:54-70`; persistence test `test_app.py:136` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `_send` `app.py:134-142`; 201/200/204/400/404/405 across `_route` |
| R9 | Input validation: title & author required | ✓ implemented | `validate_book` `app.py:31-36`→400; matrix `test_app.py:58-74` |
| R10 | GET /health health check | ✓ implemented | `app.py:175-178` → 200 `{"status":"ok"}`; `test_app.py:41` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` Setup/Run/Test/Endpoints sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 13 test functions, `test_coverage=0.92>0` |

No requirement is stubbed; each is exercised by at least one test.

## Build & Test

Not re-run — stored mechanical scores used per skill policy:

```text
scores.json: test_coverage=0.92  defect_rate=1.0  code_quality=0.789
             maintainability=1.0  idiomatic=0.85   token_efficiency=0.038
# defect_rate=1.0 ⇒ build + full suite executed and passed; coverage 92%.
```

```text
pytest (as stored): 13 functions + 7 parametrised cases, 0 skipped, 0 failed.
Tests drive the real ThreadingHTTPServer on an ephemeral port against a temp
SQLite file (integration, not mocked). grep for skip/xfail markers: 0.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 389 (app.py 238, test_app.py 151) |
| Files (non-artifact) | 12 |
| Dependencies | 1 (pytest, dev-only; zero runtime deps — stdlib only) |
| Tests total | 13 functions (~19 cases w/ parametrize) |
| Tests effective | ~19 (0 skipped) |
| Skip ratio | 0% |
| Build/test | pass (defect_rate=1.0) |
| Coverage | 92% |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, none affect pass/fail:

1. [info] Coverage 92%, not 100% — 411/413 body-length branches and the defensive 500 handler are untested (`app.py:144-168`).
2. [info] PUT is full-replacement, not partial — a valid, README-documented choice (`app.py:194-195`, `README.md:50-51`).

Clean run: all 12 pinned requirements implemented and tested, build+tests pass, zero skipped tests, no correctness defects found.

## Reproduce

```bash
cd experiments/adrianco/experiment-94-fable52-screen/rest-api-crud/runs/effort=low_language=python_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                                  # stored mechanical scores (no re-run)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0 skips
# optional live re-run:
python3 -m venv venv && venv/bin/pip install -r requirements-dev.txt && venv/bin/python -m pytest
```
