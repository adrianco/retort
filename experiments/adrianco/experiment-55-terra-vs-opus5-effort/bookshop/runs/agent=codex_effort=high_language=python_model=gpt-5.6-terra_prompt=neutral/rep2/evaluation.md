# Evaluation: agent=codex effort=high language=python model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=high, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `defect_rate=1.0`, `test_coverage=0.89` in retort.db/scores.json
- **Build:** pass — stdlib only, no build step (test_coverage=0.89 ⇒ tests executed and passed)
- **Lint:** pass — code_quality=0.79 (from scores.json)
- **Architecture:** run-summary skill unavailable; single-module WSGI app (`app.py`) + integration tests (`test_app.py`)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:85 _create_book`, INSERT at `app.py:91`, 201 + Location `app.py:96` |
| R2 | GET /books lists all | ✓ implemented | `app.py:99 _list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:102-108` parses `author`, adds `WHERE author = ?`; test `test_list_can_be_filtered_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:115 _get_book`, 404 via `_not_found` `app.py:118` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:121 _update_book`, UPDATE + 404 on miss |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:134 _delete_book`, 204 / 404 on miss |
| R7 | SQLite persistence | ✓ implemented | `app.py:30-44 _initialize_database`, sqlite3 throughout |
| R8 | JSON responses + status codes | ✓ implemented | `_json_response` `app.py:180`; 201/200/204/400/404/405/500 in `_reason_phrase` `app.py:203` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:154-158` rejects empty/non-string; test `test_title_and_author_are_required` |
| R10 | GET /health | ✓ implemented | `app.py:51-52` returns `{"status":"ok"}`; test `test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/API/Test sections |
| R12 | ≥3 tests | ✓ implemented | 5 tests in `test_app.py`, 0 skipped |

## Build & Test

```text
# No build step — pure Python stdlib (wsgiref, sqlite3, json). No dependencies.
```

```text
python3 -m unittest -v
# Stored result: test_coverage=0.89, defect_rate=1.0 (build+tests passed).
# 5 tests defined, 0 skipped → 5 effective.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 294 (app.py 212, test_app.py 82) |
| Files | 10 (incl. logs/coverage; 3 deliverables: app.py, test_app.py, README.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (no build step) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both info-level:

1. [info] Full-stdlib WSGI implementation (no framework, no deps) — a strength.
2. [info] PUT is a full replace requiring title+author (PUT semantics; noted for cross-run comparison).

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=high_language=python_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json                      # stored mechanical scores (no re-run of build/test)
grep -rE "def test_" test_app.py     # 5 tests
grep -rE "skip|xfail" *.py           # 0 skips
python3 -m unittest -v               # optional re-run (stdlib only)
```
