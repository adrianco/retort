# Evaluation: agent=claude-code effort=medium language=python model=claude-opus-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5, agent=claude-code, effort=medium, prompt=neutral, framework=Flask (inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 test functions (several parametrized → more effective cases) / 0 failed / 0 skipped — `test_coverage=0.99`, `defect_rate=1.0` from scores.json
- **Build:** pass (import/collection succeeded — `test_coverage=0.99` ⇒ tests executed) — not re-run
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Architecture:** `run-summary` skill unavailable in this session — see file table below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Using the pinned `REQUIREMENTS.json` checklist (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:95-105` INSERT + 201 + Location header |
| R2 | GET /books lists all books | ✓ implemented | `app.py:107-118` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:109-115` WHERE author = ? COLLATE NOCASE; test `test_list_books_filters_by_author` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:120-125` `_fetch`; 404 when absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:127-138` UPDATE; 404 on rowcount 0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:140-147` DELETE; 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:7-39` sqlite3 schema + connection; `test_data_survives_a_new_app_instance` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py` jsonify throughout; 200/201/204/400/404/405/503; error handlers `app.py:78-85` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:56-70` `validate_book`; `test_create_rejects_invalid_payloads` |
| R10 | GET /health health check | ✓ implemented | `app.py:87-93` probes DB, returns 503 on error |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:15-49` setup/run/test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` 16 test functions; `test_coverage=0.99` |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
# from scores.json
test_coverage = 0.99   # build + tests executed and passed
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.833
maintainability = 0.881
idiomatic     = 0.88
```

```text
# test discovery (grep)
16 def test_ functions in test_app.py; several @pytest.mark.parametrize cases expand this
0 skipped / xfail markers
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + db.py) | 204 |
| Lines of code (tests) | 179 |
| Files (source + tests + docs) | app.py, db.py, test_app.py, README.md, requirements.txt |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 16 functions (+ parametrized expansions) |
| Tests effective | 16+ (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no defects:

1. [info] All error responses (incl. framework 404/405/malformed-JSON) are JSON — `app.py:82-85`
2. [info] Validation exceeds spec: rejects bool/out-of-range years, lists all errors — `app.py:43-53`
3. [info] Health check probes the DB and returns 503 on failure — `app.py:87-93`

No requirement gaps, no skipped tests, no build/test/lint failures.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=medium_language=python_model=claude-opus-5_prompt=neutral/rep2"
cat scores.json                                  # stored mechanical scores
python3 -m pytest -q                             # optional: re-run tests
grep -cE "def test_" test_app.py                 # test count
grep -rE "pytest\.skip|xfail" . --include="*.py" # skip count (0)
```
